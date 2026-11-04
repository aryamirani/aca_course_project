#include "bimodal_param.h"

#include <algorithm>
#include <cstdlib>
#include <fmt/core.h>

void bimodal_param::initialize_branch_predictor()
{
  const char* v = std::getenv("BIMODAL_LOG_SIZE");
  int log_size = std::clamp((v != nullptr && *v != '\0') ? std::atoi(v) : 14, 4, 26);
  table.assign(std::size_t{1} << log_size, 1);
  fmt::print("BIMODAL config: log_size={} storage_kb={:.2f}\n", log_size, static_cast<double>(std::size(table)) * 2 / 8 / 1024);
}

bool bimodal_param::predict_branch(champsim::address ip) { return table[ip.to<uint64_t>() & (std::size(table) - 1)] >= 2; }

void bimodal_param::last_branch_result(champsim::address ip, champsim::address, bool taken, uint8_t)
{
  auto& c = table[ip.to<uint64_t>() & (std::size(table) - 1)];
  if (taken && c < 3)
    ++c;
  else if (!taken && c > 0)
    --c;
}
