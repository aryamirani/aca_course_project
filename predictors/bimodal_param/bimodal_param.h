#ifndef BRANCH_BIMODAL_PARAM_H
#define BRANCH_BIMODAL_PARAM_H

#include <cstdint>
#include <vector>

#include "modules.h"

// bimodal with a run-time table size, for storage-matched comparisons with TAGE.
//   BIMODAL_LOG_SIZE  log2(#2-bit counters) (default 14)
struct bimodal_param : champsim::modules::branch_predictor {
  std::vector<uint8_t> table;

  using branch_predictor::branch_predictor;

  void initialize_branch_predictor();
  bool predict_branch(champsim::address ip);
  void last_branch_result(champsim::address ip, champsim::address branch_target, bool taken, uint8_t branch_type);
};

#endif
