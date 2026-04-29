#include <pybind11/pybind11.h>
#include <pybind11/stl.h> // Auto converts Python lists to C++ std::vector
#include <vector>
#include <random>

namespace py = pybind11;

std::mt19937 globalRNG(time(0));

// The engine is now completely stateless. Python will query the MySQL DB,
// get the recent plays, and pass them into this function.
int getAIPrediction(const std::vector<int> &recentPlays, bool aiIsBatting, int difficulty) {
    std::uniform_int_distribution<> dis(0, 6);

    // LEVEL 1: NOVICE
    if (difficulty == 1) {
        return dis(globalRNG);
    }

    // LEVEL 2: TACTICIAN
    if (difficulty == 2) {
        std::uniform_int_distribution<> coinFlip(0, 1);
        if (coinFlip(globalRNG) == 0) {
            return dis(globalRNG);
        } 
    }

    // LEVEL 3: CLAIRVOYANT + Fallback
    if (recentPlays.size() < 3) {
        return dis(globalRNG);
    }

    // -- Pattern Recognition Engine --
    int frequencies[7] = {0, 0, 0, 0, 0, 0, 0};
    for (int play : recentPlays) {
        if (play >= 0 && play <= 6) {
            frequencies[play]++;
        }
    }

    int mostFrequentNum = 0, maxCount = 0;
    for (int i = 0; i <= 6; i++) {
        if (frequencies[i] > maxCount) {
            maxCount = frequencies[i];
            mostFrequentNum = i;
        }
    }

    // Execute Strategy
    if (!aiIsBatting) {
        return mostFrequentNum;
    } else {
        int leastFrequentNum = 0, minCount = frequencies[0];
        for (int i = 1; i <= 6; i++) {
            if (frequencies[i] < minCount) {
                minCount = frequencies[i];
                leastFrequentNum = i;
            }
        }
        return leastFrequentNum;
    }
}

// -- Pybind11 Binding Block --
// "handcricket_ai" - module imported from Python
PYBIND11_MODULE(handcricket_ai, m) {
    m.doc() = "C++ High-Speed Engine for Pitch.io";

    // Bind C++ Function to Python
    m.def("get_ai_prediction", &getAIPrediction, 
        "Analyzes recent plays to predict the next move",
        py::arg("recent_plays"), 
        py::arg("ai_is_batting"), 
        py::arg("difficulty")
    );
}