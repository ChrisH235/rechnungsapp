import os
import customtkinter as ctk
from tkinter import filedialog, messagebox, simpledialog
from PIL import Image, ImageTk
from tkcalendar import DateEntry
from datetime import datetime
import subprocess

from database_manager import DatabaseManager
from data_analytics import DataAnalytics

class InvoiceApp(ctk.CTk):
    def __init__(self):
        super().__init__()

        self.title("Rechnungs- & Erinnerungs-App")
        self.geometry("1100x750")
        
        ctk.set_appearance_mode("Light")
        ctk.set_default_color_theme("green")

        self.image_path = None
        self.pdf_path = None
        self.categories_map = {} 
        self.selected_invoice_id = None 

        self.db_manager = DatabaseManager() 
        self.data_analytics = DataAnalytics(self.db_manager) 

        self.create_widgets() 
        self.load_categories() 
        self.check_reminders_on_start() 
        self.load_invoices_to_listbox() 

    def load_categories(self):
        categories = self.db_manager.get_categories()
        self.categories_map = {name: id for id, name in categories}
        self.category_names = ["Alle"] + sorted([name for id, name in categories])
        
        # Korrigiert: Kategorien-Comboboxen laden
        self.category_combobox.configure(values=self.category_names)
        self.category_combobox.set("Alle")
        
        category_options_for_new_invoice = sorted([name for id, name in categories])
        self.new_invoice_category_combobox.configure(values=category_options_for_new_invoice)
        if category_options_for_new_invoice: 
            self.new_invoice_category_combobox.set(category_options_for_new_invoice[0])
        else:
            self.new_invoice_category_combobox.set("Keine Kategorien") 

        if hasattr(self, 'category_add_delete_window') and self.category_add_delete_window.winfo_exists():
            self.category_listbox_add_delete.configure(state="normal")
            self.category_listbox_add_delete.delete("1.0", "end")
            for name in sorted([name for id, name in categories]):
                self.category_listbox_add_delete.insert('end', name + "\n")
            self.category_listbox_add_delete.configure(state="disabled")

    def create_widgets(self):
        input_filter_frame = ctk.CTkFrame(self, corner_radius=15, fg_color="white")
        input_filter_frame.pack(pady=(20, 10), padx=20, fill="x")
        input_filter_frame.grid_columnconfigure(0, weight=1) 
        input_filter_frame.grid_columnconfigure(1, weight=3) 
        input_filter_frame.grid_columnconfigure(2, weight=1) 
        input_filter_frame.grid_columnconfigure(3, weight=3) 

        row_counter = 0

        ctk.CTkLabel(input_filter_frame, text="Rechnungsname:", font=("Arial", 12, "bold")).grid(row=row_counter, column=0, pady=10, padx=(20, 5), sticky="w")
        self.name_input = ctk.CTkEntry(input_filter_frame, placeholder_text="Name der Rechnung", font=("Arial", 11), corner_radius=8)
        self.name_input.grid(row=row_counter, column=1, pady=10, padx=10, sticky="ew")

        ctk.CTkLabel(input_filter_frame, text="Preis (€):", font=("Arial", 12, "bold")).grid(row=row_counter, column=2, pady=10, padx=(20, 5), sticky="w")
        self.price_input = ctk.CTkEntry(input_filter_frame, placeholder_text="Preis in Euro", font=("Arial", 11), corner_radius=8)
        self.price_input.grid(row=row_counter, column=3, pady=10, padx=10, sticky="ew")
        row_counter += 1

        ctk.CTkLabel(input_filter_frame, text="Fälligkeitsdatum:", font=("Arial", 12, "bold")).grid(row=row_counter, column=0, pady=10, padx=(20, 5), sticky="w")
        self.due_date_entry = DateEntry(input_filter_frame, selectmode='day', font=("Arial", 11),
                                        date_pattern='dd.mm.yyyy', background='#4CAF50', foreground='white', borderwidth=2)
        self.due_date_entry.grid(row=row_counter, column=1, pady=10, padx=10, sticky="ew")
        self.due_date_entry.delete(0, 'end') 
        
        ctk.CTkLabel(input_filter_frame, text="Erinnerung (Künd./Verl.):", font=("Arial", 12, "bold")).grid(row=row_counter, column=2, pady=10, padx=(20, 5), sticky="w")
        self.reminder_date_entry = DateEntry(input_filter_frame, selectmode='day', font=("Arial", 11),
                                             date_pattern='dd.mm.yyyy', background='#4CAF50', foreground='white', borderwidth=2)
        self.reminder_date_entry.grid(row=row_counter, column=3, pady=10, padx=10, sticky="ew")
        self.reminder_date_entry.delete(0, 'end') 
        row_counter += 1
        
        ctk.CTkLabel(input_filter_frame, text="Kategorie:", font=("Arial", 12, "bold")).grid(row=row_counter, column=0, pady=10, padx=(20, 5), sticky="w")
        self.new_invoice_category_combobox = ctk.CTkComboBox(input_filter_frame, font=("Arial", 11), corner_radius=8)
        self.new_invoice_category_combobox.grid(row=row_counter, column=1, pady=10, padx=10, sticky="ew")
        self.new_invoice_category_combobox.set("Keine Kategorien")
        
        self.select_file_btn = ctk.CTkButton(input_filter_frame, text="📂 Rechnungsbild auswählen", font=("Arial", 12, "bold"), 
                                             command=self.select_local_file, corner_radius=8)
        self.select_file_btn.grid(row=row_counter, column=2, pady=10, padx=10, columnspan=2, sticky="ew")
        row_counter += 1

        self.save_btn = ctk.CTkButton(input_filter_frame, text="➕ Rechnung hinzufügen", font=("Arial", 12, "bold"), fg_color="#4CAF50", hover_color="#45a049",
                               command=self.save_invoice, corner_radius=8)
        self.save_btn.grid(row=row_counter, column=0, pady=10, padx=10, columnspan=4, sticky="ew")
        row_counter += 1

        filter_frame = ctk.CTkFrame(self, corner_radius=15, fg_color="white")
        filter_frame.pack(pady=10, padx=20, fill="x")
        filter_frame.grid_columnconfigure(0, weight=1)
        filter_frame.grid_columnconfigure(1, weight=3)
        filter_frame.grid_columnconfigure(2, weight=1)
        filter_frame.grid_columnconfigure(3, weight=3)
        
        ctk.CTkLabel(filter_frame, text="Filter Status:", font=("Arial", 11, "bold")).grid(row=0, column=0, padx=20, pady=10, sticky="w")
        self.status_filter_combobox = ctk.CTkComboBox(filter_frame, font=("Arial", 11), corner_radius=8,
                                                   values=["Alle", "Offen", "Bezahlt", "Erinnert"], command=self.apply_filters)
        self.status_filter_combobox.set("Alle")
        self.status_filter_combobox.grid(row=0, column=1, padx=10, pady=10, sticky="ew")

        ctk.CTkLabel(filter_frame, text="Filter Kategorie:", font=("Arial", 11, "bold")).grid(row=0, column=2, padx=(20, 5), pady=10, sticky="w")
        self.category_combobox = ctk.CTkComboBox(filter_frame, font=("Arial", 11), corner_radius=8, command=self.apply_filters)
        self.category_combobox.grid(row=0, column=3, padx=10, pady=10, sticky="ew")
        
        self.tax_filter_var = ctk.BooleanVar(value=False)
        tax_filter_check = ctk.CTkCheckBox(filter_frame, text="Nur Steuererklärung",
                                          variable=self.tax_filter_var,
                                          font=("Arial", 11, "bold"),
                                          command=self.apply_filters)
        tax_filter_check.grid(row=1, column=0, columnspan=2, padx=20, pady=10, sticky="w")

        ctk.CTkButton(filter_frame, text="⚙️ Kategorien verwalten", font=("Arial", 11), fg_color="#A9A9A9", hover_color="#8c8c8c",
               command=self.open_category_management, corner_radius=8).grid(row=1, column=2, columnspan=2, padx=10, pady=10, sticky="ew")
        
        ctk.CTkButton(filter_frame, text="📊 Statistiken anzeigen", font=("Arial", 11), fg_color="#A9A9A9", hover_color="#8c8c8c",
               command=self.show_analytics_charts, corner_radius=8).grid(row=2, column=0, columnspan=4, padx=10, pady=10, sticky="ew")

        list_frame = ctk.CTkFrame(self, corner_radius=15, fg_color="white")
        list_frame.pack(pady=10, padx=20, fill="both", expand=True)

        ctk.CTkLabel(list_frame, text="Deine Rechnungen:", font=("Arial", 15, "bold")).pack(pady=15)

        self.invoice_listbox = ctk.CTkTextbox(list_frame, font=("Consolas", 11), height=15, width=950, wrap="none", corner_radius=8)
        self.invoice_listbox.pack(side="left", fill="both", expand=True, padx=(15, 10), pady=15)
        self.invoice_listbox.bind('<Double-Button-1>', self.on_invoice_double_click)
        self.invoice_listbox.bind('<Button-1>', self.on_invoice_single_click) 
        self.invoice_listbox.configure(state="disabled")

        action_button_frame = ctk.CTkFrame(list_frame, fg_color="transparent")
        action_button_frame.pack(side="right", fill="y", padx=(5, 15), pady=15)

        ctk.CTkButton(action_button_frame, text="✅ Als 'Bezahlt' markieren", font=("Arial", 11), fg_color="#8BC34A", hover_color="#7cb342",
               command=lambda: self.update_selected_invoice_status("Bezahlt"), corner_radius=8).pack(pady=5, fill="x")
        ctk.CTkButton(action_button_frame, text="⏳ Als 'Offen' markieren", font=("Arial", 11), fg_color="#FFC107", hover_color="#ffb300", text_color="black",
               command=lambda: self.update_selected_invoice_status("Offen"), corner_radius=8).pack(pady=5, fill="x")
        ctk.CTkButton(action_button_frame, text="🔔 Als 'Erinnert' markieren", font=("Arial", 11), fg_color="#FF5722", hover_color="#f4511e",
               command=lambda: self.update_selected_invoice_status("Erinnert"), corner_radius=8).pack(pady=5, fill="x")
        
        ctk.CTkButton(action_button_frame, text="🧾 Für Steuererklärung vormerken", font=("Arial", 11), fg_color="#008CBA", hover_color="#007a9e",
               command=self.update_tax_declaration_status, corner_radius=8).pack(pady=15, fill="x")
        ctk.CTkButton(action_button_frame, text="❌ Vormerkung entfernen", font=("Arial", 11), fg_color="#607D8B", hover_color="#546E7A",
               command=self.remove_tax_declaration_status, corner_radius=8).pack(pady=5, fill="x")

        ctk.CTkButton(action_button_frame, text="🗑️ Rechnung löschen", font=("Arial", 11), fg_color="#F44336", hover_color="#e53935",
               command=self.delete_selected_invoice, corner_radius=8).pack(pady=15, fill="x")
        
        self.status_label = ctk.CTkLabel(self, text="Bereit", font=("Arial", 12), text_color="green")
        self.status_label.pack(pady=10, padx=20, fill="x")

    def select_local_file(self):
        file_path = filedialog.askopenfilename(
            title="Rechnungsbild auswählen",
            filetypes=[("Bilddateien", "*.jpg *.jpeg *.png *.bmp *.tiff"), ("Alle Dateien", "*.*")]
        )
        if file_path:
            self.image_path = file_path
            base_name = os.path.splitext(os.path.basename(file_path))[0]
            dir_name = os.path.dirname(file_path)
            self.pdf_path = os.path.join(dir_name, base_name + ".pdf")
            
            self.status_label.configure(text=f"✅ Datei ausgewählt: {os.path.basename(file_path)}", text_color="green")
            
            self.name_input.delete(0, 'end')
            self.name_input.insert(0, base_name)
        else:
            self.status_label.configure(text="Auswahl abgebrochen.", text_color="gray")
            self.image_path = None
            self.pdf_path = None
            self.name_input.delete(0, 'end')

    def save_invoice(self):
        invoice_name = self.name_input.get().strip()
        price_str = self.price_input.get().replace(',', '.').strip()
        
        if not invoice_name:
            messagebox.showwarning("Fehlender Name", "Bitte geben Sie einen Namen für die Rechnung ein.")
            return

        try:
            amount = float(price_str) if price_str else None
        except ValueError:
            messagebox.showerror("Ungültiger Preis", "Der Preis muss eine Zahl sein.")
            return

        if self.image_path is None:
            if not messagebox.askyesno("Kein Bild ausgewählt", "Möchten Sie die Rechnung ohne ein Bild speichern?"):
                return
            
            self.image_path = None
            self.pdf_path = None
            self.status_label.configure(text="Kein Bild ausgewählt. Rechnung wird ohne Bild gespeichert.", text_color="orange")
        else:
            self.convert_image_to_pdf(self.image_path, self.pdf_path)

        try:
            due_date_str = self.due_date_entry.get_date().strftime('%Y-%m-%d')
        except ValueError:
            due_date_str = None
        
        try:
            reminder_date_str = self.reminder_date_entry.get_date().strftime('%Y-%m-%d')
        except ValueError:
            reminder_date_str = None

        selected_category_name = self.new_invoice_category_combobox.get()
        category_id = self.categories_map.get(selected_category_name) 

        status = "Offen" 
        
        if self.db_manager.add_invoice(invoice_name, amount, self.image_path, self.pdf_path, status, due_date_str, reminder_date_str, category_id):
            self.status_label.configure(text=f"✅ Rechnung '{invoice_name}' hinzugefügt.", text_color="green")
            messagebox.showinfo("Erfolgreich", f"Rechnung '{invoice_name}' erfolgreich hinzugefügt!")
            
            self.name_input.delete(0, 'end') 
            self.price_input.delete(0, 'end')
            self.due_date_entry.delete(0, 'end')
            self.reminder_date_entry.delete(0, 'end')
            if self.new_invoice_category_combobox.cget("values"):
                 self.new_invoice_category_combobox.set(self.new_invoice_category_combobox.cget("values")[0])
            else:
                self.new_invoice_category_combobox.set("")
            self.image_path = None
            self.pdf_path = None
            self.load_invoices_to_listbox()
        else:
            messagebox.showerror("Fehler", f"Rechnung '{invoice_name}' konnte nicht hinzugefügt werden.")
            self.status_label.configure(text=f"❌ Fehler beim Hinzufügen von Rechnung '{invoice_name}'.", text_color="red")

    def convert_image_to_pdf(self, image_path, pdf_path):
        try:
            img = Image.open(image_path).convert("RGB")
            img.save(pdf_path, "PDF", resolution=100.0)
            print(f"Bild erfolgreich in PDF konvertiert: {pdf_path}")
            self.status_label.configure(text=self.status_label.cget("text") + f" & PDF gespeichert: {os.path.basename(pdf_path)}", text_color="green")
        except Exception as e:
            print(f"Fehler bei der PDF-Konvertierung: {e}")
            messagebox.showerror("PDF-Konvertierungsfehler", f"Fehler beim Konvertieren zu PDF: {e}")
            self.status_label.configure(text=self.status_label.cget("text") + f" ❌ PDF-Konvertierungsfehler.", text_color="red")

    def apply_filters(self, event=None):
        self.selected_invoice_id = None 
        self.load_invoices_to_listbox()

    def load_invoices_to_listbox(self):
        self.invoice_listbox.configure(state="normal")
        self.invoice_listbox.delete("1.0", "end") 

        current_status_filter = self.status_filter_combobox.get()
        current_category_filter = self.category_combobox.get()
        current_tax_filter = self.tax_filter_var.get()

        invoices = self.db_manager.get_invoices(current_status_filter, current_category_filter, current_tax_filter)
        self.invoice_data = {} 

        # NEU: Spalten für den Preis hinzugefügt
        header_format = "{:<5} {:<30} {:<10} {:<10} {:<12} {:<15} {:<15} {:<3}"
        self.invoice_listbox.insert("end", header_format.format("ID", "Name", "Preis", "Status", "Fällig", "Erinnerung", "Kategorie", "🧾") + "\n")
        self.invoice_listbox.insert("end", "-" * 115 + "\n")

        for invoice in invoices:
            invoice_id, name, amount, image_path, pdf_path, _, status, due_date, reminder_date, tax_year, category_name = invoice
            
            due_display = due_date if due_date else "N/A"
            reminder_display = reminder_date if reminder_date else "N/A"
            category_display = category_name if category_name else "Keine"
            amount_display = f"{amount:.2f} €" if amount is not None else "N/A"

            display_name = (name[:28] + '..') if len(name) > 28 else name
            display_category = (category_display[:13] + '..') if len(category_display) > 13 else category_display
            tax_icon = "✓" if tax_year else " "

            display_text = header_format.format(
                invoice_id,
                display_name,
                amount_display,
                status,
                due_display,
                reminder_display,
                display_category,
                tax_icon
            )

            self.invoice_listbox.insert("end", display_text + "\n", f"invoice_line_{invoice_id}")
            self.invoice_data[invoice_id] = invoice 
        
        self.invoice_listbox.configure(state="disabled")

    def on_invoice_single_click(self, event):
        try:
            line_num = int(self.invoice_listbox.index(ctk.CURRENT).split('.')[0])
            if line_num <= 2: 
                self.clear_selection()
                return

            selected_item_text = self.invoice_listbox.get(f"{line_num}.0", f"{line_num}.end").strip()
            invoice_id = int(selected_item_text.split()[0]) 

            self.clear_selection()
            self.selected_invoice_id = invoice_id
            
            self.invoice_listbox.tag_add("highlight", f"{line_num}.0", f"{line_num}.end")
            self.invoice_listbox.tag_config("highlight", background="#dddddd")
        except:
            self.clear_selection()
            pass

    def clear_selection(self):
        self.invoice_listbox.tag_remove("highlight", "1.0", "end")
        self.selected_invoice_id = None

    def on_invoice_double_click(self, event):
        if self.selected_invoice_id is not None:
            invoice_tuple = self.invoice_data.get(self.selected_invoice_id)
            if invoice_tuple:
                pdf_path = invoice_tuple[4]
                if pdf_path and os.path.exists(pdf_path):
                    try:
                        if os.name == 'nt':
                            os.startfile(pdf_path)
                        elif os.uname().sysname == 'Darwin':
                            subprocess.call(['open', pdf_path])
                        else:
                            subprocess.call(['xdg-open', pdf_path])
                        self.status_label.configure(text=f"Öffne PDF: {os.path.basename(pdf_path)}", text_color="blue")
                    except Exception as e:
                        messagebox.showerror("Fehler beim Öffnen", f"Konnte PDF nicht öffnen: {e}")
                        self.status_label.configure(text="❌ Fehler beim Öffnen der PDF.", text_color="red")
                else:
                    messagebox.showwarning("PDF nicht gefunden", "Die zugehörige PDF-Datei existiert nicht mehr.")
                    self.status_label.configure(text="⚠️ PDF nicht gefunden.", text_color="orange")
    
    def get_selected_invoice_id(self):
        if self.selected_invoice_id is None:
            messagebox.showwarning("Keine Auswahl", "Bitte wählen Sie eine Rechnung aus der Liste aus.")
            return None
        return self.selected_invoice_id

    def update_selected_invoice_status(self, new_status):
        invoice_id = self.get_selected_invoice_id()
        if invoice_id is not None:
            if self.db_manager.update_invoice_status(invoice_id, new_status):
                self.status_label.configure(text=f"Status von Rechnung ID {invoice_id} auf '{new_status}' geändert.", text_color="blue")
                self.load_invoices_to_listbox()
                self.clear_selection()
            else:
                self.status_label.configure(text=f"Fehler beim Aktualisieren des Status für Rechnung ID {invoice_id}.", text_color="red")

    def delete_selected_invoice(self):
        invoice_id = self.get_selected_invoice_id()
        if invoice_id is not None:
            paths = self.db_manager.get_invoice_paths(invoice_id)

            if messagebox.askyesno("Rechnung löschen", f"Sind Sie sicher, dass Sie Rechnung ID {invoice_id} löschen möchten? Dies kann nicht rückgängig gemacht werden."):
                if self.db_manager.delete_invoice(invoice_id):
                    self.status_label.configure(text=f"Rechnung ID {invoice_id} erfolgreich gelöscht.", text_color="red")
                    self.load_invoices_to_listbox() 
                    self.clear_selection()

                    if paths:
                        image_p, pdf_p = paths
                        if image_p and os.path.exists(image_p):
                            try:
                                os.remove(image_p)
                                print(f"Bilddatei gelöscht: {image_p}")
                            except OSError as e:
                                print(f"Fehler beim Löschen der Bilddatei {image_p}: {e}")
                        if pdf_p and os.path.exists(pdf_p):
                            try:
                                os.remove(pdf_p)
                                print(f"PDF-Datei gelöscht: {pdf_p}")
                            except OSError as e:
                                print(f"Fehler beim Löschen der PDF-Datei {pdf_p}: {e}")
                else:
                    self.status_label.configure(text=f"Fehler beim Löschen der Rechnung ID {invoice_id}.", text_color="red")
            else:
                self.status_label.configure(text="Löschen abgebrochen.", text_color="gray")
    
    def check_reminders_on_start(self):
        today_str = datetime.now().strftime('%Y-%m-%d')
        due_today, remind_today = self.db_manager.get_due_and_reminder_invoices(today_str)

        if due_today or remind_today:
            message = "Wichtige Benachrichtigungen für heute:\n\n"
            if due_today:
                message += "Fällige Rechnungen:\n"
                for name, date in due_today:
                    message += f"- {name} (fällig am {date})\n"
                message += "\n"
            
            if remind_today:
                message += "Erinnerungen (Kündigung/Verlängerung):\n"
                for name, date in remind_today:
                    message += f"- {name} (Erinnerung am {date})\n"
                message += "\n"
            
            messagebox.showinfo("Benachrichtigungen", message)
            self.status_label.configure(text="Es gibt Benachrichtigungen für heute!", text_color="orange")
        else:
            self.status_label.configure(text="Keine aktuellen Benachrichtigungen.", text_color="green")

    def open_category_management(self):
        if hasattr(self, 'category_add_delete_window') and self.category_add_delete_window.winfo_exists():
            self.category_add_delete_window.lift() 
            return

        self.category_add_delete_window = ctk.CTkToplevel(self)
        self.category_add_delete_window.title("Kategorien verwalten")
        self.category_add_delete_window.geometry("400x350")
        self.category_add_delete_window.transient(self) 
        self.category_add_delete_window.grab_set() 

        frame = ctk.CTkFrame(self.category_add_delete_window, corner_radius=10)
        frame.pack(fill="both", expand=True, padx=15, pady=15)

        ctk.CTkLabel(frame, text="Neue Kategorie hinzufügen:", font=("Arial", 11, "bold")).pack(pady=5)
        self.new_category_entry = ctk.CTkEntry(frame, font=("Arial", 10), width=30, corner_radius=8)
        self.new_category_entry.pack(pady=5)
        ctk.CTkButton(frame, text="Hinzufügen", command=self.add_new_category, font=("Arial", 10), corner_radius=8).pack(pady=5)

        ctk.CTkLabel(frame, text="Bestehende Kategorien:", font=("Arial", 11, "bold")).pack(pady=10)
        
        self.category_listbox_add_delete = ctk.CTkTextbox(frame, font=("Arial", 10), height=5, width=300, corner_radius=8)
        self.category_listbox_add_delete.pack(fill="both", expand=True, padx=5, pady=5)
        
        self.load_categories_for_management_listbox() 

        ctk.CTkButton(frame, text="Ausgewählte Kategorie löschen", command=self.delete_selected_category, font=("Arial", 10), fg_color="#F44336", hover_color="#e53935", corner_radius=8).pack(pady=10)

        self.category_add_delete_window.protocol("WM_DELETE_WINDOW", self.on_category_window_close)

    def load_categories_for_management_listbox(self):
        self.category_listbox_add_delete.configure(state="normal")
        self.category_listbox_add_delete.delete("1.0", "end")
        categories = self.db_manager.get_categories()
        for id, name in sorted(categories, key=lambda x: x[1]):
            self.category_listbox_add_delete.insert('end', name + "\n")
        self.category_listbox_add_delete.configure(state="disabled")

    def add_new_category(self):
        new_cat_name = self.new_category_entry.get().strip()
        if new_cat_name:
            if self.db_manager.add_category(new_cat_name):
                self.new_category_entry.delete(0, 'end')
                self.load_categories() 
                self.load_categories_for_management_listbox() 
                self.status_label.configure(text=f"Kategorie '{new_cat_name}' hinzugefügt.", text_color="blue")
            else:
                messagebox.showerror("Fehler", f"Kategorie '{new_cat_name}' existiert bereits oder ein anderer Fehler ist aufgetreten.")
                self.status_label.configure(text=f"Kategorie '{new_cat_name}' konnte nicht hinzugefügt werden.", text_color="red")
        else:
            messagebox.showwarning("Eingabe fehlt", "Bitte geben Sie einen Namen für die neue Kategorie ein.")

    def delete_selected_category(self):
        try:
            line_num = int(self.category_listbox_add_delete.index(ctk.CURRENT).split('.')[0])
            selected_cat_name = self.category_listbox_add_delete.get(f"{line_num}.0", f"{line_num}.end").strip()
        except:
            messagebox.showwarning("Keine Auswahl", "Bitte wählen Sie eine Kategorie zum Löschen aus.")
            return
        
        if not selected_cat_name:
            messagebox.showwarning("Keine Auswahl", "Bitte wählen Sie eine Kategorie zum Löschen aus.")
            return

        category_id_to_delete = self.categories_map.get(selected_cat_name) 

        if category_id_to_delete is not None:
            if messagebox.askyesno("Kategorie löschen", f"Sind Sie sicher, dass Sie die Kategorie '{selected_cat_name}' löschen möchten?\nAlle zugeordneten Rechnungen verlieren ihre Kategorie."):
                if self.db_manager.delete_category(category_id_to_delete):
                    self.load_categories() 
                    self.load_categories_for_management_listbox() 
                    self.status_label.configure(text=f"Kategorie '{selected_cat_name}' gelöscht.", text_color="red")
                    self.load_invoices_to_listbox() 
                else:
                    messagebox.showerror("Fehler", f"Kategorie '{selected_cat_name}' konnte nicht gelöscht werden.")
                    self.status_label.configure(text=f"Fehler beim Löschen von Kategorie '{selected_cat_name}'.", text_color="red")
        else:
            messagebox.showerror("Fehler", "Kategorie-ID konnte nicht gefunden werden.")

    def on_category_window_close(self):
        self.category_add_delete_window.grab_release()
        self.category_add_delete_window.destroy()
        self.load_invoices_to_listbox() 
        self.status_label.configure(text="Kategorienverwaltung geschlossen.", text_color="gray")
    
    def show_analytics_charts(self):
        self.data_analytics.display_all_charts()
        self.status_label.configure(text="Statistiken in neuem Fenster angezeigt.", text_color="blue")
        
    def update_tax_declaration_status(self):
        invoice_id = self.get_selected_invoice_id()
        if invoice_id is None:
            return

        current_year = datetime.now().year
        year_str = simpledialog.askstring("Steuererklärung markieren",
                                        f"Für welches Jahr soll diese Rechnung (ID: {invoice_id}) vorgemerkt werden?",
                                        initialvalue=str(current_year))

        if year_str:
            try:
                year = int(year_str)
                if self.db_manager.set_invoice_for_tax_declaration(invoice_id, year):
                    self.status_label.configure(text=f"Rechnung ID {invoice_id} für die Steuererklärung {year} vorgemerkt.", text_color="blue")
                    self.load_invoices_to_listbox()
                    self.clear_selection()
                else:
                    self.status_label.configure(text=f"Fehler beim Markieren von Rechnung ID {invoice_id}.", text_color="red")
            except ValueError:
                messagebox.showerror("Ungültige Eingabe", "Bitte geben Sie eine gültige Jahreszahl ein.")
    
    def remove_tax_declaration_status(self):
        invoice_id = self.get_selected_invoice_id()
        if invoice_id is None:
            return

        if messagebox.askyesno("Vormerkung entfernen", f"Soll die Vormerkung für die Steuererklärung für Rechnung ID {invoice_id} entfernt werden?"):
            if self.db_manager.set_invoice_for_tax_declaration(invoice_id, None):
                self.status_label.configure(text=f"Vormerkung für Rechnung ID {invoice_id} entfernt.", text_color="blue")
                self.load_invoices_to_listbox()
                self.clear_selection()
            else:
                self.status_label.configure(text=f"Fehler beim Entfernen der Vormerkung für Rechnung ID {invoice_id}.", text_color="red")

if __name__ == '__main__':
    app = InvoiceApp()
    app.mainloop()