// Trace-driven branch predictor driver.
//
// Replays a ChampSim trace through the *same* predictor sources that ChampSim builds
// (branch/<name>/<name>.cc), calling predict_branch() and then last_branch_result() for every
// branch in program order, exactly as O3_CPU::do_predict_branch() does. There is no pipeline
// timing model, so it is ~50x faster than a full ChampSim run, which makes long-window MPKI
// sweeps practical. IPC still comes from full ChampSim runs.
//
// Branch classification is copied from ooo_model_instr in ChampSim/inc/instruction.h.
//
// usage:
//   bp_driver extract <trace.xz> <out.br> <max_instructions>
//       decode a trace once into a compact branch-only file (one 16-byte record per branch)
//   bp_driver <predictor> <trace.xz|trace.br> <warmup_instructions> <measured_instructions>
//       predictor: bimodal | gshare | bimodal_param | gshare_param | tage
//       run-time predictor parameters come from the same environment variables ChampSim uses.

#include <algorithm>
#include <cstdio>
#include <cstdlib>
#include <string>
#include <vector>
#include <fmt/core.h>

#include "instruction.h"
#include "modules.h"
#include "trace_instruction.h"

#include "../ChampSim/branch/bimodal/bimodal.h"
#include "../ChampSim/branch/bimodal_param/bimodal_param.h"
#include "../ChampSim/branch/gshare/gshare.h"
#include "../ChampSim/branch/gshare_param/gshare_param.h"
#include "../ChampSim/branch/tage/tage.h"

namespace
{
branch_type classify(const input_instr& in, bool& taken)
{
  auto count = [](const unsigned char* regs, std::size_t n, unsigned char r) { return std::count(regs, regs + n, r) > 0; };
  const auto* dst = in.destination_registers;
  const auto* src = in.source_registers;

  bool writes_sp = count(dst, NUM_INSTR_DESTINATIONS, champsim::REG_STACK_POINTER);
  bool writes_ip = count(dst, NUM_INSTR_DESTINATIONS, champsim::REG_INSTRUCTION_POINTER);
  bool reads_sp = count(src, NUM_INSTR_SOURCES, champsim::REG_STACK_POINTER);
  bool reads_flags = count(src, NUM_INSTR_SOURCES, champsim::REG_FLAGS);
  bool reads_ip = count(src, NUM_INSTR_SOURCES, champsim::REG_INSTRUCTION_POINTER);
  bool reads_other = std::any_of(src, src + NUM_INSTR_SOURCES, [](unsigned char r) {
    return r != 0 && r != champsim::REG_STACK_POINTER && r != champsim::REG_FLAGS && r != champsim::REG_INSTRUCTION_POINTER;
  });

  taken = true;
  if (!reads_sp && !reads_flags && writes_ip && !reads_other)
    return BRANCH_DIRECT_JUMP;
  if (!reads_sp && !reads_ip && !reads_flags && writes_ip && reads_other)
    return BRANCH_INDIRECT;
  if (!reads_sp && reads_ip && !writes_sp && writes_ip && (reads_flags || reads_other)) {
    taken = in.branch_taken;
    return BRANCH_CONDITIONAL;
  }
  if (reads_sp && reads_ip && writes_sp && writes_ip && !reads_flags && !reads_other)
    return BRANCH_DIRECT_CALL;
  if (reads_sp && reads_ip && writes_sp && writes_ip && !reads_flags && reads_other)
    return BRANCH_INDIRECT_CALL;
  if (reads_sp && !reads_ip && writes_sp && writes_ip)
    return BRANCH_RETURN;
  if (writes_ip) {
    taken = in.branch_taken;
    return BRANCH_OTHER;
  }
  taken = false;
  return NOT_BRANCH;
}

struct branch_record {
  uint64_t ip;
  uint32_t instr; // index of the instruction in the trace
  uint8_t type;
  uint8_t taken;
  uint16_t pad;
};
static_assert(sizeof(branch_record) == 16);

bool ends_with(const std::string& s, const std::string& suffix)
{
  return s.size() >= suffix.size() && s.compare(s.size() - suffix.size(), suffix.size(), suffix) == 0;
}

// Streams branch records from either an .xz ChampSim trace or an extracted .br file.
// Returns the number of instructions covered (all instructions for .xz, the stored total for .br).
template <typename F>
uint64_t for_each_branch(const std::string& trace, uint64_t limit, F&& fn)
{
  if (ends_with(trace, ".br")) {
    FILE* f = std::fopen(trace.c_str(), "rb");
    if (f == nullptr)
      return 0;
    uint64_t total = 0;
    std::fread(&total, sizeof(total), 1, f);
    std::vector<branch_record> buf(1 << 16);
    for (std::size_t n; (n = std::fread(buf.data(), sizeof(branch_record), buf.size(), f)) > 0;)
      for (std::size_t i = 0; i < n; ++i)
        if (buf[i].instr < limit)
          fn(buf[i]);
    std::fclose(f);
    return std::min(total, limit);
  }

  std::string cmd = "xz -dc '" + trace + "'";
  FILE* pipe = popen(cmd.c_str(), "r");
  if (pipe == nullptr)
    return 0;
  std::vector<input_instr> buf(1 << 16);
  uint64_t instr = 0;
  while (instr < limit) {
    std::size_t n = std::fread(buf.data(), sizeof(input_instr), buf.size(), pipe);
    if (n == 0)
      break;
    for (std::size_t i = 0; i < n && instr < limit; ++i, ++instr) {
      bool taken = false;
      auto type = classify(buf[i], taken);
      if (type != NOT_BRANCH)
        fn(branch_record{buf[i].ip, static_cast<uint32_t>(instr), static_cast<uint8_t>(type), static_cast<uint8_t>(taken), 0});
    }
  }
  pclose(pipe);
  return instr;
}

int extract(const std::string& trace, const char* out, uint64_t limit)
{
  FILE* f = std::fopen(out, "wb");
  if (f == nullptr)
    return 1;
  uint64_t placeholder = 0, branches = 0;
  std::fwrite(&placeholder, sizeof(placeholder), 1, f);
  uint64_t total = for_each_branch(trace, limit, [&](const branch_record& r) {
    std::fwrite(&r, sizeof(r), 1, f);
    ++branches;
  });
  std::fseek(f, 0, SEEK_SET);
  std::fwrite(&total, sizeof(total), 1, f);
  std::fclose(f);
  fmt::print("extracted {} branches from {} instructions\n", branches, total);
  return total == limit ? 0 : 1;
}

template <typename P>
int run(const std::string& name, const std::string& trace, uint64_t warmup, uint64_t measure)
{
  P predictor{nullptr};
  if constexpr (champsim::modules::branch_predictor::has_initialize<P>)
    predictor.initialize_branch_predictor();

  uint64_t cond = 0, cond_miss = 0;
  uint64_t instr = for_each_branch(trace, warmup + measure, [&](const branch_record& r) {
    champsim::address ip{r.ip};
    bool taken = r.taken;
    bool pred = false;
    if constexpr (std::is_same_v<P, tage>)
      pred = predictor.predict_branch(ip, champsim::address{}, false, r.type);
    else
      pred = predictor.predict_branch(ip);
    predictor.last_branch_result(ip, champsim::address{}, taken, r.type);

    if (r.instr >= warmup && r.type == BRANCH_CONDITIONAL) {
      ++cond;
      cond_miss += (pred != taken);
    }
  });

  uint64_t measured = instr > warmup ? instr - warmup : 0;
  if (measured < measure) {
    fmt::print(stderr, "trace ended early: measured {} of {} instructions\n", measured, measure);
    return 1;
  }
  double mpki = 1000.0 * static_cast<double>(cond_miss) / static_cast<double>(measured);
  double acc = cond ? 100.0 * static_cast<double>(cond - cond_miss) / static_cast<double>(cond) : 0.0;
  fmt::print("RESULT predictor={} instructions={} cond_branches={} cond_miss={} mpki_cond={:.4f} accuracy={:.3f}\n", name, measured, cond, cond_miss,
             mpki, acc);
  return 0;
}
} // namespace

int main(int argc, char** argv)
{
  if (argc != 5) {
    fmt::print(stderr, "usage: {} <predictor> <trace.xz|trace.br> <warmup> <measure>\n       {} extract <trace.xz> <out.br> <max_instructions>\n", argv[0], argv[0]);
    return 2;
  }
  std::string name = argv[1];
  std::string trace = argv[2];
  uint64_t warmup = std::strtoull(argv[3], nullptr, 10);
  uint64_t measure = std::strtoull(argv[4], nullptr, 10);

  if (name == "extract")
    return extract(trace, argv[3], measure);

  if (name == "bimodal")
    return run<bimodal>(name, trace, warmup, measure);
  if (name == "gshare")
    return run<gshare>(name, trace, warmup, measure);
  if (name == "bimodal_param")
    return run<bimodal_param>(name, trace, warmup, measure);
  if (name == "gshare_param")
    return run<gshare_param>(name, trace, warmup, measure);
  if (name == "tage")
    return run<tage>(name, trace, warmup, measure);
  fmt::print(stderr, "unknown predictor {}\n", name);
  return 2;
}
