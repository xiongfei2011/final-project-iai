**♛ N-Queens Problem Solver & Visualizer (`task1_nqueens`)**

<u><span data-marker="*">UI Credit:</span> </u>
Giao diện  của bàn cờ trong `UI/Chess.py` được tham khảo vsf dựa trên [eight-queens-problem-visualizer](https://github.com/singhAmandeep007/eight-queens-problem-visualizer) của `singhAmandeep007`.*

---

## 📁 Structure

```text
task1_nqueens/
├── main.py                      
├── documents/                   
├── UI/
│   ├── __init__.py              # Khởi tạo giao diện
│   └── Chess.py                 # Giao diện đồ họa bàn cờ N-Queens & mô phỏng từng bước
└── BE/
    ├── requirements.txt         
    ├── benchmark_report.txt     # Kết quả xuất ra sau khi chạy đo hiệu năng thuật toán
    └── app/
        ├── board.py             # Biểu diễn trạng thái bàn cờ & logic kiểm tra xung đột
        ├── models.py            # Cấu trúc dữ liệu đầu vào/đầu ra và lịch sử các bước giải
        ├── benchmark.py         # Script chạy thử nghiệm, so sánh tốc độ giữa các thuật toán
        └── solvers/
            ├── base_solver.py   # Lớp cơ sở (interface) chuẩn cho mọi bộ giải
            ├── min_conflicts.py # Thuật toán tìm kiếm cục bộ Min-Conflicts
            └── sat_solver.py    # Thuật toán quy về bài toán thỏa mãn logic (PySAT)
```
