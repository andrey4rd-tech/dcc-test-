import customtkinter as ctk
import sys
import tkinter as tk
from tkinter import filedialog, messagebox
import os
import re
import subprocess
import threading
from interpreter import DCCInterpreter
from PIL import Image, ImageTk

class DcyStudio(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("DCЫ SDK Ultimate 2026")
        self.geometry("1100x800")
        ctk.set_appearance_mode("dark")

        self.project_path = None
        self.current_file = None
        self.interpreter = DCCInterpreter()
        self.interpreter.console_callback = self.log_to_console

        # --- Иконка окна ---
        try:
            # Пробуем установить иконку окна (убираем стандартное перышко)
            # Если есть файл white_icon.ico или dep.png
            icon_path = self.resource_path("dep.png")
            img = tk.PhotoImage(file=icon_path)
            self.iconphoto(False, img)
        except Exception:
            pass # Если файла нет, останется стандартная

        # --- Фон ---
        try:
            # Используем PIL для загрузки изображения
            bg_path = self.resource_path("dep.png")
            self.bg_image = ctk.CTkImage(Image.open(bg_path), size=(1100, 800))
            self.bg_label = ctk.CTkLabel(self, image=self.bg_image, text="")
            self.bg_label.place(x=0, y=0, relwidth=1, relheight=1)
        except Exception as e:
            print(f"Не удалось загрузить фон: {e}")
            self.configure(fg_color="#2D2D2D")

        # --- Лэйаут ---
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)

        # --- Файловый менеджер (слева) ---
        self.file_browser_frame = ctk.CTkFrame(self, width=200, corner_radius=0)
        self.file_browser_frame.grid(row=0, column=0, rowspan=2, sticky="nsw")
        self.file_browser_label = ctk.CTkLabel(self.file_browser_frame, text="Проект", font=ctk.CTkFont(size=16, weight="bold"))
        self.file_browser_label.pack(pady=10)
        self.file_listbox = tk.Listbox(self.file_browser_frame, bg="#2B2B2B", fg="white", selectbackground="#007ACC", relief="flat", borderwidth=0, font=("Consolas", 11))
        self.file_listbox.pack(expand=True, fill="both", padx=5, pady=5)
        self.file_listbox.bind("<Double-1>", self.open_selected_file)

        # --- Редактор кода (центр) ---
        self.editor_frame = ctk.CTkFrame(self, corner_radius=0, fg_color="transparent")
        self.editor_frame.grid(row=0, column=1, sticky="nsew")
        # Делаем редактор полупрозрачным для фона
        self.editor = ctk.CTkTextbox(self.editor_frame, font=("Consolas", 14), wrap="none", 
                                     fg_color="#1E1E1E", text_color="#D4D4D4", border_width=0)
        self.editor.pack(expand=True, fill="both")
        self.editor.bind("<KeyRelease>", self.on_key_release)

        # --- Консоль (низ) ---
        self.console = ctk.CTkTextbox(self, height=200, font=("Consolas", 12), fg_color="#1E1E1E", text_color="white")
        self.console.grid(row=1, column=1, sticky="nsew", padx=(0, 10), pady=10)

        # --- Меню ---
        self.create_menu()

        # --- Настройка тегов для подсветки и консоли ---
        self.setup_tags()

        # --- Создание репозитория библиотек ---
        self.create_library_repo()

        # --- Автодополнение ---
        self.suggestion_window = None

        self.log_to_console("[SYSTEM] Студия DCЫ готова к работе. Создайте или откройте проект.\n", "system")

    def resource_path(self, relative_path):
        """Получает абсолютный путь к ресурсу, работает для dev и для PyInstaller"""
        try:
            # PyInstaller создает временную папку и хранит путь в _MEIPASS
            base_path = sys._MEIPASS
        except Exception:
            base_path = os.path.abspath(".")
        return os.path.join(base_path, relative_path)

    def create_menu(self):
        menubar = tk.Menu(self)
        
        file_menu = tk.Menu(menubar, tearoff=0)
        file_menu.add_command(label="Новый проект...", command=self.new_project)
        file_menu.add_command(label="Открыть проект...", command=self.open_project)
        file_menu.add_separator()
        file_menu.add_command(label="Сохранить файл", command=self.save_current_file)
        file_menu.add_separator()
        file_menu.add_command(label="Выход", command=self.quit)
        menubar.add_cascade(label="Файл", menu=file_menu)

        build_menu = tk.Menu(menubar, tearoff=0)
        build_menu.add_command(label="Запустить", command=self.run_script)
        build_menu.add_command(label="Скомпилировать в EXE", command=self.compile_to_exe)
        menubar.add_cascade(label="Сборка", menu=build_menu)

        lib_menu = tk.Menu(menubar, tearoff=0)
        lib_menu.add_command(label="Менеджер библиотек", command=self.open_library_manager)
        menubar.add_cascade(label="Библиотеки", menu=lib_menu)

        self.config(menu=menubar)

    def setup_tags(self):
        # Теги редактора
        self.editor.tag_config("DIRECTIVE", foreground="#C586C0")
        self.editor.tag_config("KEYWORD", foreground="#569CD6")
        self.editor.tag_config("TYPE", foreground="#4EC9B0")
        self.editor.tag_config("FUNCTION", foreground="#DCDCAA")
        self.editor.tag_config("STRING", foreground="#CE9178")
        self.editor.tag_config("COMMENT", foreground="#6A9955")
        self.editor.tag_config("BLOCK", foreground="#D2691E")
        # Теги консоли
        self.console.tag_config("stdout", foreground="white")
        self.console.tag_config("error", foreground="#f44747")
        self.console.tag_config("warning", foreground="#f4b400")
        self.console.tag_config("system", foreground="#58a6ff")
        self.console.tag_config("success", foreground="#34A853")

    def on_key_release(self, event=None):
        self.highlight_syntax()
        self.check_autocomplete(event)

    def check_autocomplete(self, event):
        if event.keysym in ["Up", "Down", "Return", "Escape", "BackSpace", "space"]:
            if self.suggestion_window:
                self.suggestion_window.destroy()
                self.suggestion_window = None
            return

        # Получаем текущее слово
        text = self.editor.get("1.0", "insert")
        # Разрешаем # в начале слова для директив
        match = re.search(r"[#\w_]+$", text)
        if not match:
            return
        
        current_word = match.group(0)
        if len(current_word) < 2:
            return

        keywords = ["цел", "плав", "буква", "состав", "если", "иначе", "пока", "вернуть", 
                    "пауза", "прервать", "продолжить", "ошибка", "выделить", "освободить",
                    "#библиотека", "#объявить", "#включить", "#диалог", "#память",
                    "адрес", "значение", "окно_создать", "среднее", "сумма", "макс", "мин", "корень"]
        
        suggestions = [k for k in keywords if k.startswith(current_word)]
        
        if suggestions:
            self.show_suggestions(suggestions, current_word)

    def show_suggestions(self, suggestions, current_word):
        if self.suggestion_window:
            self.suggestion_window.destroy()

        # Получаем точные координаты курсора ввода
        try:
            bbox = self.editor._textbox.bbox("insert")
            if bbox:
                x, y, w, h = bbox
                x += self.editor._textbox.winfo_rootx()
                y += self.editor._textbox.winfo_rooty() + h
            else:
                raise ValueError
        except:
            # Если не удалось получить координаты, используем позицию мыши
            x = self.winfo_pointerx()
            y = self.winfo_pointery() + 20

        self.suggestion_window = tk.Toplevel(self)
        self.suggestion_window.wm_overrideredirect(True)
        self.suggestion_window.geometry(f"+{x}+{y}")
        
        listbox = tk.Listbox(self.suggestion_window, bg="#252526", fg="white", selectbackground="#007ACC", font=("Consolas", 10))
        listbox.pack()
        
        for s in suggestions:
            listbox.insert(tk.END, s)
            
        listbox.bind("<Double-Button-1>", lambda e: self.apply_suggestion(listbox, current_word))
        listbox.bind("<Return>", lambda e: self.apply_suggestion(listbox, current_word))
        listbox.selection_set(0)
        listbox.focus_set()

    def apply_suggestion(self, listbox, current_word):
        if not listbox.curselection(): return
        selected = listbox.get(listbox.curselection()[0])
        
        # Удаляем введенную часть
        self.editor.delete(f"insert-{len(current_word)}c", "insert")
        # Вставляем полное слово
        self.editor.insert("insert", selected)
        
        self.suggestion_window.destroy()
        self.suggestion_window = None
        self.editor.focus_set()
        self.highlight_syntax()

    def highlight_syntax(self, event=None):
        rules = [
            (r'//.*', "COMMENT"),
            (r'/\*[\s\S]*?\*/', "COMMENT"),
            (r'(#библиотека|#диалог|#память|#объявить|#включить)', "DIRECTIVE"),
            (r'\b(цел|плав|буква|пусто|если|иначе|пока|вернуть|пауза|прервать|продолжить|ошибка)\b', "KEYWORD"),
            (r'\b(состав|ссылка_цел|ссылка_плав)\b', "TYPE"),
            (r'\b(да|адрес|значение|окно_создать|выделить|освободить|размер_типа|среднее|сумма|макс|мин|корень)\b', "FUNCTION"),
            (r'(подключение:|отключение:0;)', "BLOCK"),
            (r'"[^"]*"', "STRING"),
        ]
        content = self.editor.get("1.0", "end-1c")
        
        for tag in self.editor.tag_names():
            if tag != "sel": self.editor.tag_remove(tag, "1.0", "end")

        for pattern, tag in rules:
            for match in re.finditer(pattern, content):
                start = f"1.0 + {match.start()} chars"
                end = f"1.0 + {match.end()} chars"
                self.editor.tag_add(tag, start, end)

    def log_to_console(self, message, tag="stdout"):
        self.console.configure(state="normal")
        self.console.insert("end", message, (tag,))
        self.console.configure(state="disabled")
        self.console.see("end")

    def new_project(self):
        path = filedialog.askdirectory(title="Выберите папку для нового проекта")
        if not path: return

        try:
            os.makedirs(path, exist_ok=True)
            main_dcy_path = os.path.join(path, "main.dc")
            grafika_dcy_path = os.path.join(path, "grafika.dc")

            with open(main_dcy_path, "w", encoding="utf-8") as f:
                f.write("""#библиотека <ntstart.v>

подключение:
    // Пиши свой код здесь
    
отключение:0;
}""")
            
            self.open_project(path)
            self.log_to_console(f"[SYSTEM] Проект успешно создан в '{path}'\n", "success")
        except Exception as e:
            messagebox.showerror("Ошибка", f"Не удалось создать проект: {e}")

    def open_project(self, path=None):
        if not path:
            path = filedialog.askdirectory(title="Выберите папку проекта")
        if not path: return

        self.project_path = path
        os.chdir(self.project_path)
        self.update_file_browser()
        self.title(f"DCЫ SDK - {os.path.basename(path)}")

    def update_file_browser(self):
        self.file_listbox.delete(0, "end")
        if self.project_path:
            for item in sorted(os.listdir(self.project_path)):
                if item.endswith(".dc") or item.endswith(".v") or not "." in item:
                    self.file_listbox.insert("end", item)

    def open_selected_file(self, event=None):
        selected_indices = self.file_listbox.curselection()
        if not selected_indices: return
        
        filename = self.file_listbox.get(selected_indices[0])
        filepath = os.path.join(self.project_path, filename)
        
        try:
            with open(filepath, "r", encoding="utf-8") as f:
                content = f.read()
            self.editor.delete("1.0", "end")
            self.editor.insert("1.0", content)
            self.current_file = filepath
            self.highlight_syntax()
        except Exception as e:
            messagebox.showerror("Ошибка", f"Не удалось открыть файл: {e}")

    def save_current_file(self):
        if not self.current_file:
            messagebox.showwarning("Внимание", "Нет открытого файла для сохранения.")
            return
        try:
            content = self.editor.get("1.0", "end-1c")
            with open(self.current_file, "w", encoding="utf-8") as f:
                f.write(content)
            self.log_to_console(f"[SYSTEM] Файл '{os.path.basename(self.current_file)}' сохранен.\n", "system")
        except Exception as e:
            messagebox.showerror("Ошибка", f"Не удалось сохранить файл: {e}")

    def run_script(self):
        if not self.current_file:
            messagebox.showerror("Ошибка", "Откройте файл для запуска.")
            return
        
        self.save_current_file()
        self.console.configure(state="normal")
        self.console.delete("1.0", "end")
        self.console.configure(state="disabled")

        code = self.editor.get("1.0", "end-1c")
        
        # Запускаем в отдельном потоке, чтобы не блокировать UI
        threading.Thread(target=self.interpreter.execute, args=(code,), daemon=True).start()

    def compile_to_exe(self):
        if not self.project_path:
            messagebox.showerror("Ошибка", "Откройте проект для компиляции.")
            return
        
        self.log_to_console("--- Начало компиляции в EXE ---\n", "system")

        try:
            result = subprocess.run(["pyinstaller", "--version"], check=True, capture_output=True, text=True)
            self.log_to_console(f"[BUILD] Найден PyInstaller: {result.stdout.strip()}\n", "system")
        except (subprocess.CalledProcessError, FileNotFoundError):
            self.log_to_console("[BUILD] ОШИБКА: PyInstaller не найден.\n", "error")
            self.log_to_console("[BUILD] Установите его командой: pip install pyinstaller\n", "warning")
            return

        build_thread = threading.Thread(target=self._execute_compilation, daemon=True)
        build_thread.start()

    def _execute_compilation(self):
        main_file = os.path.join(self.project_path, "main.dc")
        if not os.path.exists(main_file):
            self.log_to_console("[BUILD] ОШИБКА: В проекте отсутствует файл 'main.dc'.\n", "error")
            return

        with open(main_file, "r", encoding="utf-8") as f:
            user_code = f.read()

        # Создаем runner-скрипт
        runner_code = f"""
import sys, os, re, time

# --- КОД ИНТЕРПРЕТАТОРА DCC EMBEDDED ---
{self.get_interpreter_source()}
# --- КОНЕЦ КОДА ИНТЕРПРЕТАТОРА ---

DCC_CODE = r'''
{user_code}
'''

if __name__ == "__main__":
    # Устанавливаем рабочий каталог, чтобы #включить работал
    if getattr(sys, 'frozen', False):
        os.chdir(sys._MEIPASS)
    
    interpreter = DCCInterpreter()
    interpreter.execute(DCC_CODE)
    input("\\n--- Выполнение завершено. Нажмите Enter для выхода. ---")
"""
        runner_path = os.path.join(self.project_path, "build_runner.py")
        with open(runner_path, "w", encoding="utf-8") as f:
            f.write(runner_code)

        self.log_to_console("[BUILD] Запуск PyInstaller... Это может занять некоторое время.\n", "system")
        
        exe_name = os.path.basename(self.project_path)
        command = [
            "pyinstaller",
            "--onefile",
            "--name", exe_name,
            runner_path
        ]
        
        process = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, encoding='utf-8', errors='replace')
        
        while True:
            output = process.stdout.readline()
            if output == '' and process.poll() is not None:
                break
            if output:
                self.log_to_console(output, "stdout")
        
        if process.returncode == 0:
            self.log_to_console(f"\n[BUILD] УСПЕХ! Ваш EXE-файл находится в папке 'dist'.\n", "success")
        else:
            self.log_to_console(f"\n[BUILD] ОШИБКА СБОРКИ! Проверьте лог выше.\n", "error")
        
        os.remove(runner_path) # Очистка

    def get_interpreter_source(self):
        # В реальном приложении исходники могут быть в другом месте
        # Здесь мы просто читаем файл interpreter.py
        try:
            path = self.resource_path("interpreter.py")
            with open(path, "r", encoding="utf-8") as f:
                return f.read()
        except FileNotFoundError:
            return "# ERROR: interpreter.py not found"

    def create_library_repo(self):
        repo_path = "_repository"
        os.makedirs(repo_path, exist_ok=True)
        # Создаем примеры библиотек
        with open(os.path.join(repo_path, "dcc_math.v"), "w", encoding="utf-8") as f:
            f.write("// Библиотека математических функций")
        with open(os.path.join(repo_path, "dcc_string.v"), "w", encoding="utf-8") as f:
            f.write("// Библиотека для работы со строками")
        with open(os.path.join(repo_path, "stat.v"), "w", encoding="utf-8") as f:
            f.write("// Библиотека статистики и математики")

    def open_library_manager(self):
        messagebox.showinfo("Менеджер библиотек", "Эта функция в разработке.\nБиблиотеки можно скачать из папки '_repository' и добавить в проект вручную.")

if __name__ == "__main__":
    # Проверка зависимостей
    try:
        import customtkinter
    except ImportError:
        print("Ошибка: customtkinter не найден. Установите его: pip install customtkinter")
        exit()

    app = DcyStudio()
    app.mainloop()