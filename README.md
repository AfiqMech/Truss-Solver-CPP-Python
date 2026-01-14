# 🏗️ Truss Solver

Welcome to **Truss Solver**! This tool helps you design, analyze, and visualize bridge structures.

## 📦 How to Download from GitHub
Anyone can get this project in two ways:

### Option A: The Easy Way (Download ZIP)
1.  Click the Green **"<> Code"** button at the top right of this page.
2.  Select **"Download ZIP"**.
3.  Extract the folder to your Desktop.

### Option B: The Pro Way (Git Clone)
If you have Git installed, open your terminal and run:
```bash
git clone https://github.com/AfiqMech/Truss-Solver-CPP-Python.git
```

## 🚀 How to Run
Once you have the folder:

### 1. Prerequisites
You must have Python installed on your computer.
- **Check if you have it:** Open Command Prompt and type `python --version`.
- **Don't have it?** Download it for free from [python.org](https://www.python.org/downloads/).
  - *Make sure to check the box "Add Python to PATH" during installation!*

### 2. How to Run
It's super easy!
1. Open the folder containing these files.
2. Double-click on **`run_app.bat`**.
3. A black window will open (setting up the environment) and then your browser should magically open with the App!

### 3. Troubleshooting
- **"Python is not installed"**: Reinstall Python and ensure "Add to PATH" is checked.
- **"System Unstable"**: This means your bridge design is falling apart! Add more supports or triangles.
- **Calculations are weird?**: Make sure you didn't connect a beam to a non-existent joint.

## 📚 Lecture Notes & Documentation
If you are learning or teaching how this code works, open these files in your browser:

| File | Topic & Contents |
| :--- | :--- |
| **[`ARCHITECTURE.html`](ARCHITECTURE.html)** | **The Big Picture**<br>Visual Flowcharts of how Python talks to C++. |
| **[`PYTHON_NOTES.html`](PYTHON_NOTES.html)** | **Part 1: The Architect**<br>Explains `app.py`, Session State, and how it manages the UI. |
| **[`CPP_NOTES.html`](CPP_NOTES.html)** | **Part 2: The Engineer**<br>Explains `TrussSolver.cpp`, Stiffness Matrices, and Physics formulas. |

## 🛠️ For Developers
- **`app.py`**: The main interface code (Python).
- **`truss_engine.exe`**: The math solver (C++).
- **`requirements.txt`**: List of Python libraries needed.
