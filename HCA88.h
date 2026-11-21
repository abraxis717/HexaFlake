/* Public declarations extracted from the pinned R118 C11 implementation. */
#ifndef HEXAFLAKE_HCA88_H
#define HEXAFLAKE_HCA88_H
#include <stdint.h>
#ifdef __cplusplus
extern "C" {
#endif
int awr_abi_version(void);

double awr_fsum_probe(const double *v, int32_t n);

int awr_compact(int32_t n, const int32_t *handles, const uint8_t *live, int32_t instance_capacity,
                const int32_t *slot_rel_table, const int32_t *slot_row_table, int32_t *mark,
                int32_t *slot_rel, int32_t *slot_cmp, int32_t *rows, int32_t *nr_out, int32_t max_rows);

void awr_release_marks(int32_t nr, const int32_t *rows, int32_t *mark);

int awr_execute(int32_t n, const int32_t *slot_rel, const int32_t *slot_cmp, int32_t nr, const int32_t *rows,
                double *pool, double *buf_a, double *buf_b, double *cand,
                const int64_t *rel_off, const int32_t *members, const double *frames,
                const double *W, const double *bias, int32_t correct, double alpha, double beta,
                int32_t passes, int32_t mode, int32_t *count, int32_t *off, int32_t *list,
                int64_t *links_out, int32_t flush_subnormals);

int awr_candidates(int32_t n, const int32_t *slot_rel, const int32_t *slot_cmp, const double *cin, double *cand,
                   const int64_t *rel_off, const int32_t *members, const double *frames,
                   const double *W, const double *bias, int32_t correct, double alpha, double beta,
                   int64_t *links_out);
#ifdef __cplusplus
}
#endif
#endif
