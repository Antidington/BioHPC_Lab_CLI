#include <cassert>
#include <filesystem>
#include <fstream>
#include <iostream>
#include <vector>

#include "bhlab/kmer.hpp"
#include "bhlab/layout.hpp"
#include "bhlab/minimizer.hpp"

namespace {

std::filesystem::path write_fixture() {
  const std::filesystem::path path =
      std::filesystem::temp_directory_path() / "bhlab_core_fixture.fastq";
  std::ofstream out(path);
  out << "@r1\nACGTACGTACGT\n+\nIIIIIIIIIIII\n";
  out << "@r2\nTTTTGGGGCCCC\n+\nIIIIIIIIIIII\n";
  out << "@r3\nACGTNNACGT\n+\nIIIIIIIIII\n";
  out.close();
  return path;
}

}  // namespace

int main() {
  const auto path = write_fixture();
  const bhlab::SeqBatch aos = bhlab::load_fastx(path.string(), bhlab::Layout::AoS8);
  const bhlab::SeqBatch soa = bhlab::load_fastx(path.string(), bhlab::Layout::SoA2);
  assert(aos.size() == 2);
  assert(soa.size() == 2);
  assert(aos.skipped_reads == 1);
  assert(aos.total_bases() == 24);
  assert(soa.total_bases() == 24);

  const auto aos_counts = bhlab::count_kmers(aos, 3, bhlab::Device::CPU, 1);
  const auto soa_counts = bhlab::count_kmers(soa, 3, bhlab::Device::CPU, 1);
  assert(!aos_counts.empty());
  assert(aos_counts.size() == soa_counts.size());
  for (std::size_t i = 0; i < aos_counts.size(); ++i) {
    assert(aos_counts[i].kmer == soa_counts[i].kmer);
    assert(aos_counts[i].count == soa_counts[i].count);
  }

  const bhlab::SeqBatch converted = bhlab::convert_layout(soa, bhlab::Layout::AoS8);
  assert(converted.size() == soa.size());
  const auto converted_counts = bhlab::count_kmers(converted, 3, bhlab::Device::CPU, 1);
  assert(converted_counts.size() == aos_counts.size());

  const auto mins = bhlab::compute_minimizers(aos, 3, 2);
  assert(!mins.empty());
  assert(bhlab::kmer_string(0, 3) == "AAA");
  assert(bhlab::layout_name(soa.layout) == "soa2");

  std::filesystem::remove(path);
  std::cout << "core tests passed\n";
  return 0;
}
