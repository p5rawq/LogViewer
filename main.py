import tkinter as tk
from tkinter import messagebox


def main():
    window = tk.Tk()
    window.title("Toolkit")
    window.geometry("400x600")

    # Frame
    toolbar = tk.Frame(window)
    toolbar.pack(side="top", fill="x")

    # Label
    label = tk.Label(toolbar, text="Hallo World")
    label.pack(side="top", anchor="nw")
    #label.place(x=20, y=50)

    # CheckButton
    check_var = tk.BooleanVar()
    check = tk.Checkbutton(
        toolbar,
        text="File Select",
        variable=check_var
    )
    check.pack(side="top", anchor="nw")

    # Button
    button = tk.Button(
        toolbar,
        text="Klick",
        command=message
    )
    button.pack(side="top", anchor="nw")
    window.mainloop()


def message():
    messagebox.showinfo("Test Message", "Hallo World")

# Press the green button in the gutter to run the script.
if __name__ == '__main__':
    main()

# See PyCharm help at https://www.jetbrains.com/help/pycharm/
