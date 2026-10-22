#pragma once

#include <vector>

#include "bhlab/types.hpp"

namespace bhlab {

std::vector<Minimizer> compute_minimizers(const SeqBatch& batch, int k, int window);

}  // namespace bhlab
