#include "gshare_param.h"

#include <algorithm>
#include <cstdlib>
#include <fmt/core.h>

void gshare_param::initialize_branch_predictor()
{
  const char* v = std::getenv("GSHARE_LOG_SIZE");
  log_size = std::clamp((v != nullptr && *v != '\0') ? std::atoi(v) : 14, 4, 26);
  table.assign(std::size_t{1} << log_size, 1);
  fmt::print("GSHARE config: log_size={} hist={} storage_kb={:.2f}\n", log_size, log_size, static_cast<double>(std::size(table)) * 2 / 8 / 1024);
}

std::size_t gshare_param::index(uint64_t pc) const
{
  uint64_t mask = (uint64_t{1} << log_size) - 1;
  return (pc ^ (pc >> log_size) ^ history) & mask;
}

bool gshare_param::predict_branch(champsim::address ip) { return table[index(ip.to<uint64_t>())] >= 2; }

void gshare_param::last_branch_result(champsim::address ip, champsim::address, bool taken, uint8_t)
{
  auto& c = table[index(ip.to<uint64_t>())];
  if (taken && c < 3)
    ++c;
  else if (!taken && c > 0)
    --c;
  history = ((history << 1) | (taken ? 1 : 0)) & ((uint64_t{1} << log_size) - 1);
}
