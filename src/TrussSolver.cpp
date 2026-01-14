#include <iostream>
#include <vector>
#include <cmath>
#include <string>
#include <map>
#include <Eigen/Dense>

using namespace std;
using namespace Eigen;

// ======================================================
// 1. DATA STRUCTURES
// ======================================================
struct Node {
    int id = -1;
    double xCoordinate = 0, yCoordinate = 0;
    double appliedForceX = 0, appliedForceY = 0;
    double displacementX = 0, displacementY = 0;
    double reactionX = 0, reactionY = 0;
    bool isFixedX = false, isFixedY = false;
};

struct Beam {
    int id = -1, startNodeID = -1, endNodeID = -1;
    double youngsModulus = 0, crossSectionArea = 0, yieldStrength = 0;
    double length = 0, internalForce = 0, stress = 0, safetyFactor = 0;
    double cosineTheta = 0, sineTheta = 0;
};

// Helper: Extract values from JSON-formatted string
string extractValue(string block, string key) {
    string searchKey = "\"" + key + "\":";
    size_t start = block.find(searchKey);
    if (start == string::npos) return "";
    start += searchKey.length();
    size_t firstQuote = block.find("\"", start);
    size_t commaOrBrace = block.find_first_of(",}", start);
    if (firstQuote != string::npos && firstQuote < commaOrBrace) {
        size_t secondQuote = block.find("\"", firstQuote + 1);
        return block.substr(firstQuote + 1, secondQuote - firstQuote - 1);
    }
    return block.substr(start, commaOrBrace - start);
}

int main() {
    // ---------------------------------------------------
    // STEP 1: READ INPUT FROM PIPELINE (std::cin)
    // ---------------------------------------------------
    string jsonInput, line;
    while (getline(cin, line)) jsonInput += line;
    if (jsonInput.empty()) return 0;

    vector<Node> allNodes;
    vector<Beam> allBeams;
    size_t nodeStartPos = jsonInput.find("\"nodes\":");
    size_t elementStartPos = jsonInput.find("\"elements\":");
    string nodesChunk = jsonInput.substr(nodeStartPos, elementStartPos - nodeStartPos);
    string elementsChunk = jsonInput.substr(elementStartPos);

    size_t pos = 0;
    while ((pos = nodesChunk.find("{", pos)) != string::npos) {
        size_t end = nodesChunk.find("}", pos);
        string block = nodesChunk.substr(pos, end - pos + 1);
        Node n;
        n.id = stoi(extractValue(block, "id"));
        n.xCoordinate = stod(extractValue(block, "x"));
        n.yCoordinate = stod(extractValue(block, "y"));
        n.appliedForceX = stod(extractValue(block, "loadX"));
        n.appliedForceY = stod(extractValue(block, "loadY"));
        n.isFixedX = (extractValue(block, "isFixedX") == "true");
        n.isFixedY = (extractValue(block, "isFixedY") == "true");
        allNodes.push_back(n);
        pos = end + 1;
    }

    pos = 0;
    while ((pos = elementsChunk.find("{", pos)) != string::npos) {
        size_t end = elementsChunk.find("}", pos);
        string block = elementsChunk.substr(pos, end - pos + 1);
        Beam b;
        b.id = stoi(extractValue(block, "id"));
        b.startNodeID = stoi(extractValue(block, "start"));
        b.endNodeID = stoi(extractValue(block, "end"));
        b.youngsModulus = stod(extractValue(block, "E"));
        b.crossSectionArea = stod(extractValue(block, "A"));
        b.yieldStrength = stod(extractValue(block, "yield"));
        allBeams.push_back(b);
        pos = end + 1;
    }

    // ---------------------------------------------------
    // STEP 2: ASSEMBLY OF GLOBAL STIFFNESS MATRIX [K]
    // ---------------------------------------------------
    map<int, int> idToIndex;
    for (int i = 0; i < allNodes.size(); i++) idToIndex[allNodes[i].id] = i;

    int totalDOF = allNodes.size() * 2;
    MatrixXd GlobalK = MatrixXd::Zero(totalDOF, totalDOF);
    VectorXd GlobalF = VectorXd::Zero(totalDOF);

    for (int i = 0; i < allNodes.size(); i++) {
        GlobalF(2 * i) = allNodes[i].appliedForceX;
        GlobalF(2 * i + 1) = allNodes[i].appliedForceY;
    }

    for (auto& beam : allBeams) {
        if (idToIndex.count(beam.startNodeID) && idToIndex.count(beam.endNodeID)) {
            Node &s = allNodes[idToIndex[beam.startNodeID]], &e = allNodes[idToIndex[beam.endNodeID]];
            double dx = e.xCoordinate - s.xCoordinate, dy = e.yCoordinate - s.yCoordinate;
            
            // Formula: Length = sqrt(dx^2 + dy^2)
            beam.length = sqrt(dx * dx + dy * dy);
            if (beam.length < 1e-9) continue;
            beam.cosineTheta = dx / beam.length; beam.sineTheta = dy / beam.length;
            
            // Formula: Beam Stiffness Factor k = (E * A) / L
            double k = (beam.youngsModulus * beam.crossSectionArea) / beam.length;
            double c = beam.cosineTheta, sT = beam.sineTheta;

            // Element Stiffness Matrix formula for 2D Truss
            Matrix4d localK;
            localK <<  c*c,  c*sT, -c*c, -c*sT, 
                       c*sT, sT*sT, -c*sT, -sT*sT, 
                      -c*c, -c*sT,  c*c,  c*sT, 
                      -c*sT, -sT*sT,  c*sT,  sT*sT;
            
            int g[4] = {2*idToIndex[beam.startNodeID], 2*idToIndex[beam.startNodeID]+1, 2*idToIndex[beam.endNodeID], 2*idToIndex[beam.endNodeID]+1};
            for (int r = 0; r < 4; r++) for (int cL = 0; cL < 4; cL++) GlobalK(g[r], g[cL]) += localK(r, cL) * k;
        }
    }

    // Apply boundary conditions (pinned/roller supports)
    for (int i = 0; i < allNodes.size(); i++) {
        if (allNodes[i].isFixedX) { GlobalK.row(2*i).setZero(); GlobalK.col(2*i).setZero(); GlobalK(2*i, 2*i) = 1.0; GlobalF(2*i) = 0.0; }
        if (allNodes[i].isFixedY) { GlobalK.row(2*i+1).setZero(); GlobalK.col(2*i+1).setZero(); GlobalK(2*i+1, 2*i+1) = 1.0; GlobalF(2*i+1) = 0.0; }
    }

    // ---------------------------------------------------
    // STEP 3: SOLVE SYSTEM [K]{U} = {F} -> {U} = Displacements
    // ---------------------------------------------------
    FullPivLU<MatrixXd> solver(GlobalK);
    // Instability Detection: Check if the matrix is singular (solvable)
    if (!solver.isInvertible()) { cout << "{\"status\":\"unstable\"}"; return 0; }
    VectorXd GlobalU = solver.solve(GlobalF);

    for (int i = 0; i < allNodes.size(); i++) {
        allNodes[i].displacementX = GlobalU(2 * i);
        allNodes[i].displacementY = GlobalU(2 * i + 1);
    }

    // ---------------------------------------------------
    // STEP 4: BACK-CALCULATE ELEMENT FORCES, STRESS, SAFETY
    // ---------------------------------------------------
    for (auto& beam : allBeams) {
        Node &s = allNodes[idToIndex[beam.startNodeID]], &e = allNodes[idToIndex[beam.endNodeID]];
        
        // Formula: Elongation = projection of displacement onto beam axis
        double elong = (e.displacementX - s.displacementX) * beam.cosineTheta + (e.displacementY - s.displacementY) * beam.sineTheta;
        
        // Formula: Internal Force (F) = k * Elongation = (EA/L) * ΔL
        beam.internalForce = (beam.youngsModulus * beam.crossSectionArea / beam.length) * elong;
        
        // Formula: Axial Stress (σ) = Force / Area
        beam.stress = beam.internalForce / beam.crossSectionArea;
        
        // Formula: Factor of Safety (FS) = Yield Strength / |Stress|
        beam.safetyFactor = (abs(beam.stress) > 1e-6) ? beam.yieldStrength / abs(beam.stress) : 999.0;
        
        // Calculate Support Reactions using Statics (Equilibrium)
        s.reactionX += beam.internalForce * beam.cosineTheta; s.reactionY += beam.internalForce * beam.sineTheta;
        e.reactionX -= beam.internalForce * beam.cosineTheta; e.reactionY -= beam.internalForce * beam.sineTheta;
    }

    // ---------------------------------------------------
    // STEP 5: OUTPUT RESULTS AS JSON PIPELINE (std::cout)
    // ---------------------------------------------------
    auto sn = [](double v) { return (isnan(v) || isinf(v)) ? 0.0 : v; };
    cout << "{\"status\":\"success\",\"nodes\":[";
    for (int i = 0; i < allNodes.size(); i++) {
        if (i > 0) cout << ",";
        cout << "{\"id\":" << allNodes[i].id << ",\"ux\":" << sn(allNodes[i].displacementX) << ",\"uy\":" << sn(allNodes[i].displacementY)
             << ",\"rx\":" << sn(-(allNodes[i].reactionX + allNodes[i].appliedForceX)) << ",\"ry\":" << sn(-(allNodes[i].reactionY + allNodes[i].appliedForceY)) << "}";
    }
    cout << "],\"elements\":[";
    for (int i = 0; i < allBeams.size(); i++) {
        if (i > 0) cout << ",";
        cout << "{\"id\":" << allBeams[i].id << ",\"force\":" << sn(allBeams[i].internalForce) << ",\"stress\":" << sn(allBeams[i].stress) << ",\"safety\":" << sn(allBeams[i].safetyFactor) << "}";
    }
    cout << "]}";
    return 0;
}
