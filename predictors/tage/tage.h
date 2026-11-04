#ifndef BRANCH_TAGE_H
#define BRANCH_TAGE_H

#include <cstdint>
#include <vector>

#include "modules.h"

/*
 * Simplified TAGE branch predictor
 *   A. Seznec, P. Michaud, "A case for (partially) TAgged GEometric history length
 *   branch prediction", JILP vol. 8, 2006.
 *
 * Components
 *   - T0: bimodal base predictor (2-bit counters, PC indexed)
 *   - T1..TN: partially tagged tables, table i indexed with a hash of the PC and the
 *     L(i) most recent global history bits, where L(i) is a geometric series
 *     L(i) = Lmin * (Lmax/Lmin)^((i-1)/(N-1))
 *   - each tagged entry: 3-bit signed prediction counter, partial tag, 2-bit useful counter
 *
 * The geometry is read from environment variables when the predictor is initialised, so a
 * single binary can be swept without recompiling:
 *   TAGE_NUM_TABLES   number of tagged tables             (default 4)
 *   TAGE_MIN_HIST     shortest history length  Lmin       (default 5)
 *   TAGE_MAX_HIST     longest history length   Lmax       (default 130)
 *   TAGE_HIST_LIST    explicit comma separated lengths, overrides the geometric series
 *   TAGE_LOG_BASE     log2(#entries) of the bimodal base  (default 13)
 *   TAGE_LOG_TAGGED   log2(#entries) of each tagged table (default 10)
 *   TAGE_TAG_BITS     partial tag width in bits           (default 9)
 */
struct tage : champsim::modules::branch_predictor {
  static constexpr int MAX_TABLES = 16;
  static constexpr int HIST_BUFFER = 4096; // circular global history buffer, must exceed the longest history
  static constexpr int PATH_BITS = 16;
  static constexpr int CTR_MAX = 3, CTR_MIN = -4; // 3-bit signed prediction counter
  static constexpr int U_MAX = 3;                  // 2-bit useful counter
  static constexpr uint64_t U_RESET_PERIOD = 1 << 18;

  struct tagged_entry {
    int8_t ctr = 0;
    uint16_t tag = 0;
    uint8_t u = 0;
  };

  // History folded into comp_len bits with a circular shift register (Michaud's folding),
  // updated in O(1) per branch instead of re-hashing L(i) bits every time
  struct folded_history {
    uint32_t comp = 0;
    int comp_len = 0;
    int orig_len = 0;
    int outpoint = 0;

    void init(int original, int compressed);
    void update(const std::vector<uint8_t>& ghist, int ptr);
  };

  // geometry
  int num_tables = 4;
  int log_base = 13;
  int log_tagged = 10;
  int tag_bits = 9;
  std::vector<int> hist_len;

  // state
  std::vector<uint8_t> base;                     // 2-bit counters, 0..3
  std::vector<std::vector<tagged_entry>> tables; // tables[0] is T1 (shortest history)
  std::vector<uint8_t> ghist;
  int ptr = 0;
  uint32_t path_hist = 0;
  std::vector<folded_history> fold_idx, fold_tag0, fold_tag1;
  int8_t use_alt_on_na = 0; // 4-bit signed: trust altpred over a newly allocated provider?
  uint64_t branch_count = 0;
  bool reset_msb = true;
  uint32_t rng = 0x2545F491;

  // lookup results, filled by predict_branch and consumed by last_branch_result
  uint64_t last_ip = 0;
  std::vector<uint32_t> idx;
  std::vector<uint16_t> tag;
  int provider = -1; // index into tables, -1 = base predictor
  int alt = -1;
  bool provider_pred = false;
  bool alt_pred = false;
  bool final_pred = false;
  bool provider_weak = false;

  using branch_predictor::branch_predictor;

  void initialize_branch_predictor();
  bool predict_branch(champsim::address ip, champsim::address predicted_target, bool always_taken, uint8_t branch_type);
  void last_branch_result(champsim::address ip, champsim::address branch_target, bool taken, uint8_t branch_type);

private:
  void lookup(uint64_t pc);
  uint32_t index_hash(uint64_t pc, int table) const;
  uint16_t tag_hash(uint64_t pc, int table) const;
  bool base_pred(uint64_t pc) const;
  void update_base(uint64_t pc, bool taken);
  void update_history(uint64_t pc, bool taken);
  uint32_t next_random();
  double storage_kb() const;
};

#endif
