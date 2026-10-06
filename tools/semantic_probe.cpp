#include "../app/src/main/cpp/semantic_core.h"
#include <iostream>
#include <chrono>
#include <fstream>
#include <sstream>

int main(int argc, char **argv) {
    if (argc != 3) return 2;
    SemanticCore model(argv[1], 2);
    model.cancel();
    if (!model.rank("Cancelled request", 2, 1000).empty()) return 17;
    model.arm();
    std::ifstream input(argv[2]);
    std::string line;
    while (std::getline(input, line)) {
        std::istringstream row(line); int count; row >> count;
        std::string path; row >> path;
        std::ifstream prompt_file(path); std::stringstream prompt; prompt << prompt_file.rdbuf();
        auto start = std::chrono::steady_clock::now();
        auto values = model.rank(prompt.str(), count, 60000);
        auto elapsed = std::chrono::duration_cast<std::chrono::milliseconds>(std::chrono::steady_clock::now()-start).count();
        std::cout << elapsed;
        for (float value : values) std::cout << '\t' << value;
        std::cout << std::endl;
    }
}
