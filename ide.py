import tkinter as tk
import os
from tkinter import filedialog, scrolledtext, messagebox
import re
from interpreter import DCCInterpreter
import subprocess

class DCCEditor:
    def __init__(self, root):
        self.root = root
        self.root.title("DCC IDE - Редактор кода")
        self.root.geometry("800x600")
        
        self.filename = None
        self.interpreter = DCCInterpreter()
        self.interpreter.console_callback = self.log_output_wrapper
        self.interpreter.set_dialog_callback(self.show_system_dialog)

        # Установка фонового изображения
        try:
            self.bg_image = tk.PhotoImage(file="dep.png")
            bg_label = tk.Label(self.root, image=self.bg_image)
            bg_label.place(x=0, y=0, relwidth=1, relheight=1)
        except tk.TclError:
            self.root.config(bg="#2D2D2D") # Запасной фон, если картинка не найдена

        # Создание библиотек в папке проекта
        self.create_libs()

        # --- UI Компоненты ---
        
        # Меню
        menubar = tk.Menu(self.root)
        file_menu = tk.Menu(menubar, tearoff=0)
        file_menu.add_command(label="Новый", command=self.new_file)
        file_menu.add_command(label="Открыть", command=self.open_file)
        file_menu.add_command(label="Сохранить", command=self.save_file)
        file_menu.add_command(label="Сохранить как...", command=self.save_file_as)
        file_menu.add_separator()
        file_menu.add_command(label="Выход", command=root.quit)
        menubar.add_cascade(label="Файл", menu=file_menu)
        
        run_menu = tk.Menu(menubar, tearoff=0)
        run_menu.add_command(label="Запустить скрипт", command=self.run_script)
        menubar.add_cascade(label="Запуск", menu=run_menu)
        
        build_menu = tk.Menu(menubar, tearoff=0)
        build_menu.add_command(label="Скомпилировать в EXE", command=self.compile_exe)
        menubar.add_cascade(label="Сборка", menu=build_menu)

        self.root.config(menu=menubar)

        # Панель инструментов (Toolbar)
        toolbar = tk.Frame(self.root, bg="#33373A", bd=1, relief=tk.RAISED)
        btn_style = {'bg': '#4A4F52', 'fg': 'white', 'relief': 'flat', 'padx': 5, 'pady': 5, 'font': ('Segoe UI', 9)}

        new_btn = tk.Button(toolbar, text="Новый", command=self.new_file, **btn_style)
        new_btn.pack(side=tk.LEFT, padx=2, pady=2)
        open_btn = tk.Button(toolbar, text="Открыть", command=self.open_file, **btn_style)
        open_btn.pack(side=tk.LEFT, padx=2)
        save_btn = tk.Button(toolbar, text="Сохранить", command=self.save_file, **btn_style)
        save_btn.pack(side=tk.LEFT, padx=2)
        run_btn = tk.Button(toolbar, text="▶ Запуск", command=self.run_script, bg="#5C965C", fg="white", relief='flat', padx=5, pady=5, font=('Segoe UI', 9, 'bold'))
        run_btn.pack(side=tk.LEFT, padx=(10, 2))
        toolbar.pack(side=tk.TOP, fill=tk.X)

        # Основной редактор кода
        self.text_area = scrolledtext.ScrolledText(self.root, wrap=tk.WORD, font=("Consolas", 12), 
                                                   bg="#1E1E1E", fg="#D4D4D4", insertbackground="white")
        self.text_area.pack(expand=True, fill='both', padx=5, pady=5)
        
        # Привязка события для подсветки синтаксиса при вводе
        self.text_area.bind('<KeyRelease>', self.highlight_syntax)
        self.text_area.bind('<KeyRelease>', self.check_hints, add='+')

        # Область вывода (консоль)
        self.console_label = tk.Label(self.root, text="Вывод:", anchor="w", bg="#252526", fg="white")
        self.console_label.pack(fill='x', padx=5)
        
        self.console = scrolledtext.ScrolledText(self.root, height=8, bg="#1E1E1E", fg="#0f0", font=("Consolas", 10), insertbackground="white")
        self.console.pack(fill='x', padx=5, pady=5)

        # Статус бар для подсказок
        self.status_bar = tk.Label(self.root, text="Готов", bd=1, relief=tk.SUNKEN, anchor=tk.W, bg="#007ACC", fg="white")
        self.status_bar.pack(side=tk.BOTTOM, fill=tk.X)

        # Настройка тегов для подсветки
        self.setup_tags()
        
        # Начальный шаблон
        self.new_file()

    def create_libs(self):
        """Создает файлы библиотек, если они не существуют"""
        if not os.path.exists("ntstart.v"):
            with open("ntstart.v", "w", encoding="utf-8") as f:
                f.write("// Базовая библиотека DCC\n// Версия 1.0")
            self.log_output("[IDE] Файл библиотеки ntstart.v создан.\n")

        if not os.path.exists("ntsvtart.v"):
            with open("ntsvtart.v", "w", encoding="utf-8") as f:
                f.write("// Библиотека диалогов DCC\n// Версия 1.0\n// Системный файл")
            self.log_output("[IDE] Файл библиотеки ntsvtart.v создан в папке проекта.\n")
        
        if not os.path.exists("int.v"):
            with open("int.v", "w", encoding="utf-8") as f:
                f.write("// Библиотека интерфейса DCC\n// Версия 1.0\n// Системный файл")
            self.log_output("[IDE] Файл библиотеки int.v создан в папке проекта.\n")
        
        if not os.path.exists("ntmem.v"):
            with open("ntmem.v", "w", encoding="utf-8") as f:
                f.write("// Библиотека управления памятью DCC\n// Версия 1.0\n// Системный файл")
            self.log_output("[IDE] Файл библиотеки ntmem.v создан в папке проекта.\n")
            
        if not os.path.exists("ntwin_api.v"):
            with open("ntwin_api.v", "w", encoding="utf-8") as f:
                f.write("// Библиотека Windows API для DCC\n// Версия 1.0\n// Системный файл")
            self.log_output("[IDE] Файл библиотеки ntwin_api.v создан в папке проекта.\n")

    def show_system_dialog(self, message):
        messagebox.showinfo("Сообщение DCC", message)

    def setup_tags(self):
        """Настройка цветов для синтаксиса"""
        # Цвета для темной темы
        # Директивы (#библиотека) - Розовый/Фиолетовый
        self.text_area.tag_config("DIRECTIVE", foreground="#C586C0", font=("Consolas", 12, "bold"))
        # Библиотека (<ntstart.v>) - Светло-голубой
        self.text_area.tag_config("LIBRARY", foreground="#9CDCFE")
        # Блоки (подключение:, отключение:) - Оранжевый/Коричневый
        self.text_area.tag_config("BLOCK", foreground="#D2691E", font=("Consolas", 12, "bold")) # Точки входа
        # Ключевые слова (цел, если, иначе, пока) - Синий (как в VS)
        self.text_area.tag_config("KEYWORD", foreground="#569CD6", font=("Consolas", 12, "bold"))
        # Структуры и типы (состав, ссылка_цел) - Бирюзовый
        self.text_area.tag_config("TYPE", foreground="#4EC9B0", font=("Consolas", 12, "bold"))
        # Функции (да) - Желтый/Бежевый
        self.text_area.tag_config("FUNCTION", foreground="#DCDCAA")
        # Строки ("...") - Оранжево-красный
        self.text_area.tag_config("STRING", foreground="#CE9178")
        # Комментарии - Зеленый
        self.text_area.tag_config("COMMENT", foreground="#6A9955")

    def highlight_syntax(self, event=None):
        """Логика подсветки текста"""
        content = self.text_area.get("1.0", tk.END)
        
        # Очистка старых тегов
        for tag in self.text_area.tag_names():
            self.text_area.tag_remove(tag, "1.0", tk.END)

        # Правила regex для подсветки
        rules = [
            (r'//.*', "COMMENT"),
            (r'/\*[\s\S]*?\*/', "COMMENT"),
            (r'(#библиотека|#диалог|#интерфейс|#память|#объявить|#включить)', "DIRECTIVE"),
            (r'<[^>]+>', "LIBRARY"),
            (r'(подключение:|отключение:0;)', "BLOCK"),
            (r'\b(цел|плав|буква|пусто|если|иначе|пока|вернуть|пауза|прервать|продолжить|ошибка)\b', "KEYWORD"),
            (r'\b(состав|ссылка_цел|ссылка_плав)\b', "TYPE"),
            (r'\b(да|адрес|значение|окно_создать|выделить|освободить|размер_типа)\b', "FUNCTION"),
            (r'"[^"]*"', "STRING"),
            (r'\b\w+\.\w+\b', "STRING"), # Подсветка полей структур (простая)
        ]

        for pattern, tag in rules:
            for match in re.finditer(pattern, content):
                start = f"1.0+{match.start()}c"
                end = f"1.0+{match.end()}c"
                self.text_area.tag_add(tag, start, end)

    def check_hints(self, event=None):
        """Простая система подсказок в статус-баре"""
        try:
            current_pos = self.text_area.index(tk.INSERT)
            line_start = current_pos.split('.')[0] + ".0"
            line_text = self.text_area.get(line_start, current_pos).strip()
            words = line_text.split()
            if words:
                last_word = words[-1]
                hints = {
                    "состав": "состав Имя { поле; } — объявление структуры",
                    "адрес": "адрес(переменная) — получение ссылки",
                    "значение": "значение(ссылка) — разыменование",
                    "окно_создать": "окно_создать(заголовок, ш, в)",
                    "#библиотека": "#библиотека <имя.v>",
                    "выделить": "выделить(размер) — malloc",
                }
                if last_word in hints:
                    self.status_bar.config(text=f"Подсказка: {hints[last_word]}")
                else:
                    self.status_bar.config(text="Готов")
        except:
            pass

    def log_output_wrapper(self, message, tag=None):
        """Вывод сообщений в нижнюю консоль"""
        self.console.insert(tk.END, message)
        self.console.see(tk.END)

    def run_script(self):
        """Запуск интерпретатора"""
        code = self.text_area.get("1.0", tk.END)
        self.console.delete("1.0", tk.END) # Очистить консоль
        self.interpreter.execute(code)

    def compile_exe(self):
        """Имитация компиляции"""
        self.log_output("--- Начало сборки проекта ---\n")
        code = self.text_area.get("1.0", tk.END)
        
        # 1. Генерация Python скрипта
        py_file = self.interpreter.compile_to_python(code, "game_build.py")
        self.log_output(f"[BUILD] Сгенерирован промежуточный код: {py_file}\n")
        
        # 2. Инструкция для PyInstaller
        self.log_output("[BUILD] Для создания EXE выполните в консоли:\n")
        self.log_output(f"pyinstaller --onefile {py_file}\n")
        
        # Попытка запуска если есть pyinstaller
        try:
            # subprocess.run(["pyinstaller", "--onefile", py_file], check=True)
            # self.log_output("[BUILD] EXE успешно создан в папке dist!\n")
            pass
        except:
            self.log_output("[WARN] PyInstaller не найден. Установите: pip install pyinstaller\n")

    def new_file(self):
        self.filename = None
        self.text_area.delete("1.0", "end")
        # Вставляем шаблон по умолчанию
        template = """#библиотека <ntstart.v>

подключение:
    // Пиши свой код здесь

отключение:0;
}"""
        self.text_area.insert("1.0", template)
        self.highlight_syntax()
        self.root.title("DCC IDE - Новый файл")

    def open_file(self):
        file_path = filedialog.askopenfilename(filetypes=[("DC Script", "*.dc"), ("All Files", "*.*")])
        if file_path:
            self.filename = file_path
            with open(file_path, "r", encoding="utf-8") as f:
                content = f.read()
            self.text_area.delete("1.0", tk.END)
            self.text_area.insert("1.0", content)
            self.highlight_syntax()
            self.root.title(f"DCC IDE - {file_path}")

    def save_file(self):
        if self.filename:
            content = self.text_area.get("1.0", tk.END)
            with open(self.filename, "w", encoding="utf-8") as f:
                f.write(content)
        else:
            self.save_file_as()

    def save_file_as(self):
        file_path = filedialog.asksaveasfilename(defaultextension=".dc",
                                                 filetypes=[("DC Script", "*.dc"), ("All Files", "*.*")])
        if file_path:
            self.filename = file_path
            self.save_file()
            self.root.title(f"DCC IDE - {file_path}")

if __name__ == "__main__":
    root = tk.Tk()
    app = DCCEditor(root)
    root.mainloop()