import tkinter as tk
from UI.Chess import NQueensNativeGame

if __name__ == "__main__":
    app_root = tk.Tk()
    NQueensNativeGame(app_root)
    app_root.mainloop()