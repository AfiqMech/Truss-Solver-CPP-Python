CXX = g++
CXXFLAGS = -O3 -I./include -I./include/Eigen
TARGET = truss_engine
SRC = src/TrussSolver.cpp

all: $(TARGET)

$(TARGET): $(SRC)
	$(CXX) $(CXXFLAGS) $(SRC) -o $(TARGET)

clean:
	rm -f $(TARGET)
