#include "tage.h"

#include <algorithm>
#include <cmath>
#include <cstdlib>
#include <sstream>
#include <string>
#include <fmt/core.h>

#include "instruction.h"

namespace
{
int env_int(const char* name, int fallback)
{
  const char* v = std::getenv(name);
  return (v != nullptr && *v != '\0') ? std::atoi(v) : fallback;
}

bool is_conditional(uint8_t branch_type) { return branch_type == BRANCH_CONDITIONAL || branch_type == BRANCH_OTHER; }
} // namespace

void tage::folded_history::init(int original, int compressed)
{
  comp = 0;
  orig_len = original;
  comp_len = compressed;
  outpoint = original % compressed;
}

void tage::folded_history::update(const std::vector<uint8_t>& ghist, int ptr)
{
  // shift in the newest bit, cancel the bit that just left the L-bit window, fold the overflow bit back
  comp = (comp << 1) | ghist[ptr];
  comp ^= static_cast<uint32_t>(ghist[(ptr + orig_len) % HIST_BUFFER]) << outpoint;
  comp ^= comp >> comp_len;
  comp &= (1u << comp_len) - 1;
}

void tage::initialize_branch_predictor()
{
  num_tables = std::clamp(env_int("TAGE_NUM_TABLES", 4), 1, MAX_TABLES);
  log_base = std::clamp(env_int("TAGE_LOG_BASE", 13), 4, 24);
  log_tagged = std::clamp(env_int("TAGE_LOG_TAGGED", 10), 4, 20);
  tag_bits = std::clamp(env_int("TAGE_TAG_BITS", 9), 4, 16);
  int min_hist = std::max(1, env_int("TAGE_MIN_HIST", 5));
  int max_hist = std::clamp(env_int("TAGE_MAX_HIST", 130), min_hist, HIST_BUFFER - 2);

  hist_len.clear();
  if (const char* list = std::getenv("TAGE_HIST_LIST"); list != nullptr && *list != '\0') {
    std::stringstream ss{list};
    for (std::string item; std::getline(ss, item, ',');)
      hist_len.push_back(std::clamp(std::atoi(item.c_str()), 1, HIST_BUFFER - 2));
    num_tables = std::clamp(static_cast<int>(std::size(hist_len)), 1, MAX_TABLES);
    hist_len.resize(num_tables);
  } else if (num_tables == 1) {
    hist_len.push_back(static_cast<int>(std::lround(std::sqrt(static_cast<double>(min_hist) * max_hist))));
  } else {
    // geometric series L(i) = Lmin * (Lmax/Lmin)^(i/(N-1))
    double ratio = static_cast<double>(max_hist) / min_hist;
    for (int i = 0; i < num_tables; ++i) {
      int len = static_cast<int>(std::lround(min_hist * std::pow(ratio, static_cast<double>(i) / (num_tables - 1))));
      if (!hist_len.empty())
        len = std::max(len, hist_len.back() + 1); // keep lengths strictly increasing
      hist_len.push_back(len);
    }
  }

  base.assign(std::size_t{1} << log_base, 2); // weakly taken
  tables.assign(num_tables, std::vector<tagged_entry>(std::size_t{1} << log_tagged));
  ghist.assign(HIST_BUFFER, 0);
  ptr = 0;
  path_hist = 0;

  fold_idx.resize(num_tables);
  fold_tag0.resize(num_tables);
  fold_tag1.resize(num_tables);
  for (int t = 0; t < num_tables; ++t) {
    fold_idx[t].init(hist_len[t], log_tagged);
    fold_tag0[t].init(hist_len[t], tag_bits);
    fold_tag1[t].init(hist_len[t], tag_bits - 1);
  }
  idx.assign(num_tables, 0);
  tag.assign(num_tables, 0);

  std::string lens;
  for (auto l : hist_len)
    lens += (lens.empty() ? "" : ",") + std::to_string(l);
  fmt::print("TAGE config: tables={} hist=[{}] log_base={} log_tagged={} tag_bits={} storage_kb={:.2f}\n", num_tables, lens, log_base, log_tagged,
             tag_bits, storage_kb());
}

double tage::storage_kb() const
{
  double base_bits = static_cast<double>(std::size(base)) * 2;
  double entry_bits = 3 + tag_bits + 2;
  double tagged_bits = static_cast<double>(num_tables) * static_cast<double>(std::size_t{1} << log_tagged) * entry_bits;
  return (base_bits + tagged_bits + 4) / 8.0 / 1024.0;
}

uint32_t tage::next_random()
{
  rng ^= rng << 13;
  rng ^= rng >> 17;
  rng ^= rng << 5;
  return rng;
}

uint32_t tage::index_hash(uint64_t pc, int t) const
{
  uint32_t path = path_hist & ((1u << std::min(hist_len[t], PATH_BITS)) - 1);
  uint64_t h = pc ^ (pc >> (std::abs(log_tagged - t) + 1)) ^ fold_idx[t].comp ^ path ^ (path >> log_tagged);
  return static_cast<uint32_t>(h & ((1u << log_tagged) - 1));
}

uint16_t tage::tag_hash(uint64_t pc, int t) const
{
  uint64_t h = pc ^ fold_tag0[t].comp ^ (static_cast<uint64_t>(fold_tag1[t].comp) << 1);
  return static_cast<uint16_t>(h & ((1u << tag_bits) - 1));
}

bool tage::base_pred(uint64_t pc) const { return base[pc & (std::size(base) - 1)] >= 2; }

void tage::update_base(uint64_t pc, bool taken)
{
  auto& c = base[pc & (std::size(base) - 1)];
  if (taken && c < 3)
    ++c;
  else if (!taken && c > 0)
    --c;
}

void tage::lookup(uint64_t pc)
{
  last_ip = pc;
  for (int t = 0; t < num_tables; ++t) {
    idx[t] = index_hash(pc, t);
    tag[t] = tag_hash(pc, t);
  }

  // provider = longest-history hit, alt = next longest hit (or the base predictor)
  provider = alt = -1;
  for (int t = num_tables - 1; t >= 0; --t) {
    if (tables[t][idx[t]].tag == tag[t]) {
      if (provider < 0) {
        provider = t;
      } else {
        alt = t;
        break;
      }
    }
  }

  alt_pred = (alt >= 0) ? tables[alt][idx[alt]].ctr >= 0 : base_pred(pc);
  if (provider >= 0) {
    const auto& e = tables[provider][idx[provider]];
    provider_pred = e.ctr >= 0;
    provider_weak = (e.ctr == 0 || e.ctr == -1) && e.u == 0; // likely a newly allocated entry
    final_pred = (provider_weak && use_alt_on_na >= 0) ? alt_pred : provider_pred;
  } else {
    provider_pred = alt_pred;
    provider_weak = false;
    final_pred = alt_pred;
  }
}

bool tage::predict_branch(champsim::address ip, champsim::address, bool, uint8_t branch_type)
{
  if (!is_conditional(branch_type))
    return true; // unconditional branches: direction is always taken, target comes from the BTB/RAS

  lookup(ip.to<uint64_t>());
  return final_pred;
}

void tage::update_history(uint64_t pc, bool taken)
{
  ptr = (ptr - 1 + HIST_BUFFER) % HIST_BUFFER;
  ghist[ptr] = taken ? 1 : 0;
  path_hist = ((path_hist << 1) | (pc & 1)) & ((1u << PATH_BITS) - 1);
  for (int t = 0; t < num_tables; ++t) {
    fold_idx[t].update(ghist, ptr);
    fold_tag0[t].update(ghist, ptr);
    fold_tag1[t].update(ghist, ptr);
  }
}

void tage::last_branch_result(champsim::address ip, champsim::address, bool taken, uint8_t branch_type)
{
  uint64_t pc = ip.to<uint64_t>();

  if (is_conditional(branch_type)) {
    if (pc != last_ip)
      lookup(pc);

    // 1. allocate a new entry in a longer-history table on a misprediction
    //    (skip it when the provider itself was right and only the alternate prediction was wrong)
    bool allocate = final_pred != taken && provider < num_tables - 1 && !(provider >= 0 && provider_weak && provider_pred == taken);
    if (allocate) {
      std::vector<int> candidates;
      for (int t = provider + 1; t < num_tables; ++t)
        if (tables[t][idx[t]].u == 0)
          candidates.push_back(t);

      if (candidates.empty()) {
        // no free entry: age the useful bits so an entry frees up later
        for (int t = provider + 1; t < num_tables; ++t)
          if (tables[t][idx[t]].u > 0)
            --tables[t][idx[t]].u;
      } else {
        // prefer the shortest candidate with probability 2/3 (Seznec & Michaud, Sec. 3.3)
        int chosen = (std::size(candidates) > 1 && next_random() % 3 == 0) ? candidates[1] : candidates[0];
        auto& e = tables[chosen][idx[chosen]];
        e.tag = tag[chosen];
        e.ctr = taken ? 0 : -1;
        e.u = 0;
      }
    }

    // 2. learn whether newly allocated providers should be trusted
    if (provider >= 0 && provider_weak && provider_pred != alt_pred)
      use_alt_on_na = static_cast<int8_t>(std::clamp(use_alt_on_na + (alt_pred == taken ? 1 : -1), -8, 7));

    // 3. update the prediction counters
    if (provider >= 0) {
      auto& e = tables[provider][idx[provider]];
      e.ctr = static_cast<int8_t>(std::clamp(e.ctr + (taken ? 1 : -1), CTR_MIN, CTR_MAX));
      if (provider_weak) {
        if (alt >= 0) {
          auto& a = tables[alt][idx[alt]];
          a.ctr = static_cast<int8_t>(std::clamp(a.ctr + (taken ? 1 : -1), CTR_MIN, CTR_MAX));
        } else {
          update_base(pc, taken);
        }
      }
    } else {
      update_base(pc, taken);
    }

    // 4. useful counter: rewarded only when the provider disagreed with the alternate prediction
    if (provider >= 0 && provider_pred != alt_pred) {
      auto& e = tables[provider][idx[provider]];
      if (provider_pred == taken && e.u < U_MAX)
        ++e.u;
      else if (provider_pred != taken && e.u > 0)
        --e.u;
    }

    // 5. graceful periodic reset of the useful counters, alternating MSB and LSB
    if (++branch_count % U_RESET_PERIOD == 0) {
      uint8_t keep_mask = reset_msb ? 0x1 : 0x2;
      for (auto& table : tables)
        for (auto& e : table)
          e.u &= keep_mask;
      reset_msb = !reset_msb;
    }

    last_ip = 0;
  }

  update_history(pc, taken);
}
