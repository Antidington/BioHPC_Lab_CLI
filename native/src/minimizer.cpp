#include "bhlab/minimizer.hpp"

#include <algorithm>
#include <stdexcept>
#include <vector>

#include "bhlab/layout.hpp"

namespace bhlab {

std::vector<Minimizer> compute_minimizers(const SeqBatch& batch, int k, int window) {
  if (k <= 0 || k > 31) throw std::runtime_error("k must be between 1 and 31");
  if (window <= 0) throw std::runtime_error("window must be positive");

  std::vector<Minimizer> out;
  for (std::size_t read = 0; read < batch.size(); ++read) {
    const std::size_t length = batch.lengths[read];
    if (length < static_cast<std::size_t>(k)) continue;
    const std::size_t kmer_count = length - static_cast<std::size_t>(k) + 1;
    if (kmer_count < static_cast<std::size_t>(window)) {
      const uint64_t only = canonical_kmer(batch, read, 0, k);
      out.push_back({static_cast<uint32_t>(read), 0, only});
      continue;
    }
    std::vector<uint64_t> kmers(kmer_count);
    for (std::size_t pos = 0; pos < kmer_count; ++pos) {
      kmers[pos] = canonical_kmer(batch, read, pos, k);
    }
    uint64_t last = 0;
    bool has_last = false;
    for (std::size_t start = 0; start + static_cast<std::size_t>(window) <= kmer_count; ++start) {
      uint64_t best = kmers[start];
      for (int offset = 1; offset < window; ++offset) {
        best = std::min(best, kmers[start + static_cast<std::size_t>(offset)]);
      }
      if (!has_last || best != last) {
        out.push_back({static_cast<uint32_t>(read), static_cast<uint32_t>(start), best});
        last = best;
        has_last = true;
      }
    }
  }
  return out;
}

}  // namespace bhlab
