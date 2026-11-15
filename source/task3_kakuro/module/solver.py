# module/solver.py
from core.csp_core import CSP, Variable
from module.inference import is_consistent, forward_checking

class CSPSolver:
    def __init__(self, csp: CSP):
        self.csp = csp
        self.history = []  # Lưu vết để truyền cho GUI Pygame

    def solve(self) -> dict:
        """Kích hoạt giải thuật"""
        return self.backtrack({})

    def backtrack(self, assignment: dict) -> dict | None:
        """Thuật toán Backtracking lõi"""
        # Điều kiện dừng: Nếu số lượng biến đã gán bằng tổng số biến
        if len(assignment) == len(self.csp.variables):
            return assignment

        # Heuristic 1: Select Unassigned Variable (MRV)
        var = self.select_unassigned_variable(assignment)

        # Heuristic 2: Order Domain Values (LCV)
        for value in self.order_domain_values(var, assignment):
            
            # Heuristic 3: Inference (Kiểm tra tính nhất quán)
            if is_consistent(self.csp, var, value, assignment):
                # Action: Gán giá trị
                assignment[var] = value
                var.value = value
                
                # Lưu log cho GUI
                self.history.append({"action": "ASSIGN", "var": var.id, "val": value})

                # Chạy Inference (Forward Checking) để tỉa nhánh
                pruned = forward_checking(self.csp, var, value, assignment)

                # Gọi đệ quy đi tiếp
                result = self.backtrack(assignment)
                if result is not None:
                    return result

                # BACKTRACK (Quay lui): Hủy gán nếu nhánh này thất bại
                del assignment[var]
                var.value = 0
                
                # Lưu log Undo cho GUI
                self.history.append({"action": "UNASSIGN", "var": var.id})

                # (Nếu có Forward Checking, phải phục hồi domain bị tỉa ở đây)

        return None # Vô nghiệm ở nhánh này

    def select_unassigned_variable(self, assignment: dict) -> Variable:
        """
        Sử dụng MRV (Minimum Remaining Values) Heuristic.
        Chọn biến có số lượng giá trị trong domain ít nhất.
        """
        unassigned_vars = [v for v in self.csp.variables if v not in assignment]
        
        # Sắp xếp biến dựa trên len(domain) tăng dần. Lấy biến đầu tiên.
        # Ở trạng thái cơ bản, ta tạm thời đếm số khả năng còn lại. 
        return min(unassigned_vars, key=lambda v: len(v.domain))

    def order_domain_values(self, var: Variable, assignment: dict) -> list[int]:
        """
        Sử dụng LCV (Least Constraining Value) Heuristic.
        (Mặc định trả về list domain thông thường. Bạn có thể sort list này 
        để ưu tiên các số ít gây ảnh hưởng tới hàng xóm nhất).
        """
        # Hiện tại cứ trả về danh sách domain cơ bản
        return list(var.domain)