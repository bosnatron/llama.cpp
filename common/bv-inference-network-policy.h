#pragma once

#include <cstdlib>
#include <stdexcept>

// BOSNATRON privacy boundary. This applies to EVERY non-empty role value,
// including misspelled/invalid roles, until server initialization rejects it.
// Inference-only child processes need no outbound HTTP clients. Local HTTP
// inference uses httplib::Server and is intentionally unaffected.
inline bool bv_inference_outbound_network_forbidden() noexcept {
    const char * role = std::getenv("BV_INFERENCE_ROLE");
    return role != nullptr && role[0] != '\0';
}

inline void bv_refuse_outbound_http_client() {
    if (bv_inference_outbound_network_forbidden()) {
        throw std::runtime_error(
            "BV inference-only mode forbids outbound HTTP clients and remote model downloads");
    }
}
