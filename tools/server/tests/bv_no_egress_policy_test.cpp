// Standalone portable unit test for the BV inference outbound HTTP boundary.
// No sockets, models, network requests, downloads or personal data used.
#include "bv-inference-network-policy.h"

#include <cstdlib>
#include <iostream>
#include <stdexcept>
#include <string>

static bool set_role(const char * role) {
#ifdef _WIN32
    return _putenv_s("BV_INFERENCE_ROLE", role ? role : "") == 0;
#else
    return role ? setenv("BV_INFERENCE_ROLE", role, 1) == 0
                : unsetenv("BV_INFERENCE_ROLE") == 0;
#endif
}

static bool denies_outbound() {
    try {
        bv_refuse_outbound_http_client();
    } catch (const std::runtime_error & error) {
        return std::string(error.what()).find("forbids outbound HTTP") != std::string::npos;
    }
    return false;
}

int main() {
    const char * const cases[] = { "chat", "embedding", "invalid", "CHAT", "bogus" };
    int checked = 0;

    if (!set_role(nullptr) || bv_inference_outbound_network_forbidden() || denies_outbound()) {
        std::cerr << "FAIL: absent role must not change general llama.cpp downloader\n";
        return 1;
    }
    ++checked;
    if (!set_role("") || bv_inference_outbound_network_forbidden() || denies_outbound()) {
        std::cerr << "FAIL: empty role must not change general llama.cpp downloader\n";
        return 1;
    }
    ++checked;
    for (const char * role : cases) {
        if (!set_role(role) ||
            !bv_inference_outbound_network_forbidden() ||
            !denies_outbound()) {
            std::cerr << "FAIL: BV role did not refuse outbound HTTP: " << role << "\n";
            return 1;
        }
        ++checked;
    }
    if (!set_role(nullptr) || bv_inference_outbound_network_forbidden() || denies_outbound()) {
        std::cerr << "FAIL: the test did not restore the local environment\n";
        return 1;
    }
    ++checked;
    std::cout << "BV_INFERENCE_NO_EGRESS_POLICY=PASS cases=" << checked
              << " outbound_requests_executed=0 release_approved=false\n";
    return 0;
}
