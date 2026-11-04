#ifndef BRANCH_GSHARE_PARAM_H
#define BRANCH_GSHARE_PARAM_H

#include <cstdint>
#include <vector>

#include "modules.h"

// gshare with a run-time table size, for storage-matched comparisons with TAGE.
//   GSHARE_LOG_SIZE  log2(#2-bit counters), history length = table index width (default 14)
struct gshare_param : champsim::modules::branch_predictor {
  int log_size = 14;
  uint64_t history = 0;
  std::vector<uint8_t> table;

  using branch_predictor::branch_predictor;

  void initialize_branch_predictor();
  bool predict_branch(champsim::address ip);
  void last_branch_result(champsim::address ip, champsim::address branch_target, bool taken, uint8_t branch_type);

private:
  std::size_t index(uint64_t pc) const;
};

#endif
