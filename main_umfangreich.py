import os
import sqlite3
from tkinter import Tk, Button, Label, Entry, filedialog, messagebox, Frame, Scrollbar, Listbox, Toplevel
from tkinter import ttk
from PIL import Image, ImageTk
from tkcalendar import DateEntry
from datetime import datetime
import subprocess # Für plattformunabhängiges Öffnen von Dateien

# --- Datenbankfunktionen ---
def create_db():
    """Erstellt die SQLite-Datenbank und Tabellen, falls sie noch nicht existieren."""
    conn = sqlite3.connect('invoice_data.db')
    cursor = conn.cursor()

    # Tabelle für Rechnungen erweitern
    # category_id INTEGER: Fremdschlüssel zur categories-Tabelle
    cursor.execute('''CREATE TABLE IF NOT EXISTS invoices (
                        id INTEGER PRIMARY KEY,
                        name TEXT,
                        image_path TEXT,
                        pdf_path TEXT,
                        creation_date TEXT,
                        status TEXT,
                        due_date TEXT,      
                        reminder_date TEXT, 
                        category_id INTEGER, 
                        FOREIGN KEY (category_id) REFERENCES categories(id)
                    )''')

    # Tabelle für Kategorien erstellen
    cursor.execute('''CREATE TABLE IF NOT EXISTS categories (
                        id INTEGER PRIMARY KEY,
                        name TEXT UNIQUE 
                    )''')
    
    # Standardkategorien hinzufügen, falls die Tabelle leer ist
    # INSERT OR IGNORE verhindert Duplikate, wenn die App mehrfach gestartet wird
    cursor.execute("INSERT OR IGNORE INTO categories (name) VALUES ('Rechnung'), ('Versicherung'), ('Miete'), ('Abonnement'), ('Sonstiges')")
    
    conn.commit()
    conn.close()

def add_invoice(name, image_path, pdf_path, status, due_date=None, reminder_date=None, category_id=None):
    """Fügt eine neue Rechnung in die Datenbank ein, jetzt mit Kategorie."""
    try:
        conn = sqlite3.connect('invoice_data.db')
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO invoices (name, image_path, pdf_path, creation_date, status, due_date, reminder_date, category_id)
            VALUES (?, ?, ?, CURRENT_TIMESTAMP, ?, ?, ?, ?)
        """, (name, image_path, pdf_path, status, due_date, reminder_date, category_id))

        conn.commit()
        print(f"Rechnung '{name}' erfolgreich hinzugefügt.")
    except sqlite3.Error as e:
        print(f"Fehler beim Hinzufügen der Rechnung: {e}")
    finally:
        if conn:
            conn.close()

def get_invoices(status_filter=None, category_filter=None):
    """
    Liest Rechnungen aus der Datenbank und gibt sie aus, optional gefiltert nach Status und/oder Kategorie.
    """
    conn = sqlite3.connect('invoice_data.db')
    cursor = conn.cursor()
    
    # LEFT JOIN, um den Kategorienamen zu erhalten, auch wenn category_id NULL ist
    query = "SELECT invoices.*, categories.name FROM invoices LEFT JOIN categories ON invoices.category_id = categories.id WHERE 1=1"
    params = []

    if status_filter and status_filter != "Alle":
        query += " AND status = ?"
        params.append(status_filter)
    
    if category_filter and category_filter != "Alle":
        query += " AND categories.name = ?"
        params.append(category_filter)

    query += " ORDER BY creation_date DESC" # Neueste Rechnungen zuerst
    
    cursor.execute(query, params)
    invoices = cursor.fetchall()
    conn.close()
    return invoices

def update_invoice_status(invoice_id, new_status):
    """Aktualisiert den Status einer Rechnung in der Datenbank."""
    try:
        conn = sqlite3.connect('invoice_data.db')
        cursor = conn.cursor()
        cursor.execute("UPDATE invoices SET status = ? WHERE id = ?", (new_status, invoice_id))
        conn.commit()
        print(f"Rechnung ID {invoice_id} Status aktualisiert auf '{new_status}'.")
    except sqlite3.Error as e:
        print(f"Fehler beim Aktualisieren des Status: {e}")
    finally:
        if conn:
            conn.close()

def delete_invoice(invoice_id):
    """Löscht eine Rechnung aus der Datenbank."""
    try:
        conn = sqlite3.connect('invoice_data.db')
        cursor = conn.cursor()
        cursor.execute("DELETE FROM invoices WHERE id = ?", (invoice_id,))
        conn.commit()
        print(f"Rechnung ID {invoice_id} erfolgreich gelöscht.")
    except sqlite3.Error as e:
        print(f"Fehler beim Löschen der Rechnung: {e}")
    finally:
        if conn:
            conn.close()

def get_categories():
    """Liest alle Kategorien aus der Datenbank."""
    conn = sqlite3.connect('invoice_data.db')
    cursor = conn.cursor()
    cursor.execute("SELECT id, name FROM categories ORDER BY name")
    categories = cursor.fetchall()
    conn.close()
    return categories

def add_category(name):
    """Fügt eine neue Kategorie hinzu."""
    try:
        conn = sqlite3.connect('invoice_data.db')
        cursor = conn.cursor()
        cursor.execute("INSERT INTO categories (name) VALUES (?)", (name,))
        conn.commit()
        print(f"Kategorie '{name}' hinzugefügt.")
        return True
    except sqlite3.IntegrityError: # Fängt UNIQUE Constraint Fehler ab
        messagebox.showerror("Fehler", f"Kategorie '{name}' existiert bereits.")
        return False
    except sqlite3.Error as e:
        print(f"Fehler beim Hinzufügen der Kategorie: {e}")
        messagebox.showerror("Fehler", f"Fehler beim Hinzufügen der Kategorie: {e}")
        return False
    finally:
        if conn:
            conn.close()

def delete_category(category_id):
    """Löscht eine Kategorie und setzt die category_id von zugehörigen Rechnungen auf NULL."""
    try:
        conn = sqlite3.connect('invoice_data.db')
        cursor = conn.cursor()
        # Zuerst Rechnungen aktualisieren, die diese Kategorie verwenden
        cursor.execute("UPDATE invoices SET category_id = NULL WHERE category_id = ?", (category_id,))
        cursor.execute("DELETE FROM categories WHERE id = ?", (category_id,))
        conn.commit()
        print(f"Kategorie ID {category_id} gelöscht.")
        return True
    except sqlite3.Error as e:
        print(f"Fehler beim Löschen der Kategorie: {e}")
        messagebox.showerror("Fehler", f"Fehler beim Löschen der Kategorie: {e}")
        return False
    finally:
        if conn:
            conn.close()


# --- Hauptanwendungsklasse ---
class InvoiceApp(Tk):
    def __init__(self):
        super().__init__()

        self.title("Rechnungs- & Erinnerungs-App")
        self.geometry("1100x750") # Etwas größer für neue Elemente
        self.configure(bg="#f0f0f0")

        self.image_path = None
        self.pdf_path = None
        self.categories_map = {} # Speichert {Kategoriename: ID} zur schnellen Zuordnung

        create_db() # Datenbank beim Start erstellen/aktualisieren
        
        # WICHTIG: Widgets zuerst erstellen, dann die Kategorien laden, die die Widgets befüllen
        self.create_widgets() 
        self.load_categories() 

        self.check_reminders_on_start() # Erinnerungen beim Start prüfen
        self.load_invoices_to_listbox() # Rechnungen beim Start laden

    def load_categories(self):
        """Lädt Kategorien aus der Datenbank und befüllt die Comboboxen."""
        categories = get_categories()
        # Erstelle eine Map von Kategoriename zu ID für die Speicherung in der DB
        self.categories_map = {name: id for id, name in categories}
        # Erstelle eine Liste von Namen für die Comboboxen (inkl. "Alle" für Filter)
        self.category_names = ["Alle"] + sorted([name for id, name in categories])
        
        # Aktualisiere die Combobox für den Filter
        self.category_combobox['values'] = self.category_names
        self.category_combobox.set("Alle") # Standardauswahl für Filter
        
        # Aktualisiere die Combobox für neue Rechnungen (ohne "Alle" Option)
        self.new_invoice_category_combobox['values'] = sorted([name for id, name in categories])
        if sorted([name for id, name in categories]): # Setze den ersten Eintrag, falls vorhanden
            self.new_invoice_category_combobox.set(sorted([name for id, name in categories])[0])
        else:
            self.new_invoice_category_combobox.set("") # Setze leer, wenn keine Kategorien

        # Aktualisiere die Listbox im Add/Delete Category Window, falls offen
        if hasattr(self, 'category_add_delete_window') and self.category_add_delete_window.winfo_exists():
            self.category_listbox_add_delete.delete(0, 'end')
            for name in sorted([name for id, name in categories]):
                self.category_listbox_add_delete.insert('end', name)

    def create_widgets(self):
        """Erstellt die GUI-Komponenten."""
        # --- Eingabe- und Filter-Frame ---
        input_filter_frame = Frame(self, bg="#ffffff", bd=2, relief="solid", padx=20, pady=15)
        input_filter_frame.pack(pady=10, padx=20, fill="x")

        # Grid-Konfiguration für 4 Spalten
        input_filter_frame.grid_columnconfigure(0, weight=1) # Labels links
        input_filter_frame.grid_columnconfigure(1, weight=3) # Eingabefelder links
        input_filter_frame.grid_columnconfigure(2, weight=1) # Labels rechts
        input_filter_frame.grid_columnconfigure(3, weight=3) # Eingabefelder rechts

        row_counter = 0

        # Rechnungsname
        Label(input_filter_frame, text="Rechnungsname:", font=("Arial", 11, "bold"), bg="#ffffff").grid(row=row_counter, column=0, pady=5, sticky="w")
        self.name_input = Entry(input_filter_frame, font=("Arial", 10), width=30, bd=1, relief="solid")
        self.name_input.grid(row=row_counter, column=1, pady=5, sticky="ew")

        # Fälligkeitsdatum
        Label(input_filter_frame, text="Fälligkeitsdatum:", font=("Arial", 11, "bold"), bg="#ffffff").grid(row=row_counter, column=2, pady=5, padx=(10,0), sticky="w")
        self.due_date_entry = DateEntry(input_filter_frame, selectmode='day', font=("Arial", 10),
                                        date_pattern='dd.mm.yyyy', background='darkblue',
                                        foreground='white', borderwidth=2)
        self.due_date_entry.grid(row=row_counter, column=3, pady=5, sticky="ew")
        self.due_date_entry.delete(0, 'end') # Startet leer
        row_counter += 1

        # Erinnerungsdatum
        Label(input_filter_frame, text="Erinnerung (Künd./Verl.):", font=("Arial", 11, "bold"), bg="#ffffff").grid(row=row_counter, column=0, pady=5, sticky="w")
        self.reminder_date_entry = DateEntry(input_filter_frame, selectmode='day', font=("Arial", 10),
                                             date_pattern='dd.mm.yyyy', background='darkblue',
                                             foreground='white', borderwidth=2)
        self.reminder_date_entry.grid(row=row_counter, column=1, pady=5, sticky="ew")
        self.reminder_date_entry.delete(0, 'end') # Startet leer
        
        # Kategorienauswahl für neue Rechnungen
        Label(input_filter_frame, text="Kategorie:", font=("Arial", 11, "bold"), bg="#ffffff").grid(row=row_counter, column=2, pady=5, padx=(10,0), sticky="w")
        self.new_invoice_category_combobox = ttk.Combobox(input_filter_frame, font=("Arial", 10), state="readonly")
        self.new_invoice_category_combobox.grid(row=row_counter, column=3, pady=5, sticky="ew")
        # Werte werden später von load_categories gesetzt
        row_counter += 1

        # Buttons für Datei auswählen und Rechnung hinzufügen
        self.select_file_btn = Button(input_filter_frame, text="📂 Rechnungsbild auswählen", font=("Arial", 11, "bold"), bg="#2196F3", fg="white", 
                                     command=self.select_local_file, relief="raised", padx=10, pady=5)
        self.select_file_btn.grid(row=row_counter, column=0, pady=10, columnspan=4, sticky="ew")
        row_counter += 1

        self.save_btn = Button(input_filter_frame, text="➕ Rechnung hinzufügen", font=("Arial", 11, "bold"), bg="#4CAF50", fg="white", 
                               command=self.save_invoice, relief="raised", padx=10, pady=5)
        self.save_btn.grid(row=row_counter, column=0, pady=10, columnspan=4, sticky="ew")
        row_counter += 1

        # --- Filter-Optionen ---
        filter_row_counter = 0
        filter_frame = Frame(input_filter_frame, bg="#f0f0f0", bd=1, relief="groove", padx=10, pady=5)
        filter_frame.grid(row=row_counter, column=0, columnspan=4, sticky="ew", pady=(15,0))
        filter_frame.grid_columnconfigure(0, weight=1)
        filter_frame.grid_columnconfigure(1, weight=3)
        filter_frame.grid_columnconfigure(2, weight=1)
        filter_frame.grid_columnconfigure(3, weight=3)

        Label(filter_frame, text="Filter Status:", font=("Arial", 10, "bold"), bg="#f0f0f0").grid(row=filter_row_counter, column=0, sticky="w", pady=2)
        self.status_filter_combobox = ttk.Combobox(filter_frame, font=("Arial", 10), state="readonly",
                                                   values=["Alle", "Offen", "Bezahlt", "Erinnert"])
        self.status_filter_combobox.set("Alle")
        self.status_filter_combobox.bind("<<ComboboxSelected>>", self.apply_filters)
        self.status_filter_combobox.grid(row=filter_row_counter, column=1, sticky="ew", pady=2)

        Label(filter_frame, text="Filter Kategorie:", font=("Arial", 10, "bold"), bg="#f0f0f0").grid(row=filter_row_counter, column=2, padx=(10,0), sticky="w", pady=2)
        self.category_combobox = ttk.Combobox(filter_frame, font=("Arial", 10), state="readonly")
        self.category_combobox.bind("<<ComboboxSelected>>", self.apply_filters)
        self.category_combobox.grid(row=filter_row_counter, column=3, sticky="ew", pady=2)
        # Werte werden später von load_categories gesetzt

        # Button für Kategorien verwalten
        filter_row_counter += 1
        Button(filter_frame, text="⚙️ Kategorien verwalten", font=("Arial", 10), bg="#A9A9A9", fg="white", 
               command=self.open_category_management, relief="raised", padx=5, pady=3).grid(row=filter_row_counter, column=0, columnspan=4, sticky="ew", pady=5)


        # --- Rechnungsliste Frame ---
        list_frame = Frame(self, bg="#ffffff", bd=2, relief="solid", padx=20, pady=10)
        list_frame.pack(pady=10, padx=20, fill="both", expand=True)

        Label(list_frame, text="Deine Rechnungen:", font=("Arial", 15, "bold"), bg="#ffffff").pack(pady=5)

        self.invoice_listbox = Listbox(list_frame, font=("Consolas", 11), height=15, selectmode="single", bd=1, relief="solid")
        self.invoice_listbox.pack(side="left", fill="both", expand=True, padx=(0, 5))
        self.invoice_listbox.bind('<Double-Button-1>', self.on_invoice_double_click)


        scrollbar = Scrollbar(list_frame, orient="vertical", command=self.invoice_listbox.yview)
        scrollbar.pack(side="right", fill="y")
        self.invoice_listbox.config(yscrollcommand=scrollbar.set)

        # Buttons für Aktionen an der ausgewählten Rechnung
        action_button_frame = Frame(list_frame, bg="#ffffff")
        action_button_frame.pack(side="right", fill="y", padx=(5, 0))

        Button(action_button_frame, text="✅ Als 'Bezahlt' markieren", font=("Arial", 10), bg="#8BC34A", fg="white", 
               command=lambda: self.update_selected_invoice_status("Bezahlt"), relief="raised", padx=5, pady=3).pack(pady=5, fill="x")
        Button(action_button_frame, text="⏳ Als 'Offen' markieren", font=("Arial", 10), bg="#FFC107", fg="black", 
               command=lambda: self.update_selected_invoice_status("Offen"), relief="raised", padx=5, pady=3).pack(pady=5, fill="x")
        Button(action_button_frame, text="🔔 Als 'Erinnert' markieren", font=("Arial", 10), bg="#FF5722", fg="white", 
               command=lambda: self.update_selected_invoice_status("Erinnert"), relief="raised", padx=5, pady=3).pack(pady=5, fill="x")
        Button(action_button_frame, text="🗑️ Rechnung löschen", font=("Arial", 10), bg="#F44336", fg="white", 
               command=self.delete_selected_invoice, relief="raised", padx=5, pady=3).pack(pady=15, fill="x")
        
        # Status Label (unten)
        self.status_label = Label(self, text="Bereit", font=("Arial", 12), fg="green", bg="#f0f0f0", wraplength=1050)
        self.status_label.pack(pady=10, padx=20, fill="x")

    # --- Datei- und Speicherfunktionen ---
    def select_local_file(self):
        """Öffnet einen Dateiauswahldialog, um eine lokale Bilddatei auszuwählen."""
        file_path = filedialog.askopenfilename(
            title="Rechnungsbild auswählen",
            filetypes=[("Bilddateien", "*.jpg *.jpeg *.png *.bmp *.tiff"), ("Alle Dateien", "*.*")]
        )
        if file_path:
            self.image_path = file_path
            self.pdf_path = os.path.splitext(file_path)[0] + ".pdf" 
            self.status_label.config(text=f"✅ Datei ausgewählt: {os.path.basename(file_path)}", fg="green")
            
            # Setze den Rechnungsnamen basierend auf dem Dateinamen
            self.name_input.delete(0, 'end')
            self.name_input.insert(0, os.path.splitext(os.path.basename(file_path))[0])
        else:
            self.status_label.config(text="Auswahl abgebrochen.", fg="gray")
            self.image_path = None
            self.pdf_path = None
            self.name_input.delete(0, 'end')

    def save_invoice(self):
        """Speichert die Rechnung in der SQLite-Datenbank und aktualisiert die Liste."""
        invoice_name = self.name_input.get().strip()
        if not invoice_name:
            messagebox.showwarning("Fehlender Name", "Bitte geben Sie einen Namen für die Rechnung ein.")
            return

        if not self.image_path:
            messagebox.showwarning("Kein Bild", "Bitte wählen Sie zuerst ein Rechnungsbild aus.")
            return

        # Fälligkeits- und Erinnerungsdatum abrufen
        try:
            due_date_str = self.due_date_entry.get_date().strftime('%Y-%m-%d')
        except ValueError: # Wenn das Feld leer oder ungültig ist
            due_date_str = None
        
        try:
            reminder_date_str = self.reminder_date_entry.get_date().strftime('%Y-%m-%d')
        except ValueError: # Wenn das Feld leer oder ungültig ist
            reminder_date_str = None

        # Kategorie abrufen
        selected_category_name = self.new_invoice_category_combobox.get()
        # Hole die ID zur Kategorie, Standard auf None, falls keine Kategorie gewählt
        category_id = self.categories_map.get(selected_category_name) 

        # Konvertiere das Bild in PDF
        self.convert_image_to_pdf(self.image_path, self.pdf_path)

        status = "Offen" # Standardstatus für neue Rechnungen
        
        add_invoice(invoice_name, self.image_path, self.pdf_path, status, due_date_str, reminder_date_str, category_id)
        
        self.status_label.config(text=f"✅ Rechnung '{invoice_name}' hinzugefügt.", fg="green")
        messagebox.showinfo("Erfolgreich", f"Rechnung '{invoice_name}' erfolgreich hinzugefügt!")
        
        # Eingabefelder zurücksetzen
        self.name_input.delete(0, 'end')
        self.due_date_entry.delete(0, 'end')
        self.reminder_date_entry.delete(0, 'end')
        self.new_invoice_category_combobox.set("") # Kategorie-Dropdown zurücksetzen
        self.image_path = None
        self.pdf_path = None
        self.load_invoices_to_listbox() # Liste aktualisieren

    def convert_image_to_pdf(self, image_path, pdf_path):
        """Konvertiert das Bild in eine PDF-Datei."""
        try:
            img = Image.open(image_path).convert("RGB")
            img.save(pdf_path, "PDF", resolution=100.0)
            print(f"Bild erfolgreich in PDF konvertiert: {pdf_path}")
            self.status_label.config(text=self.status_label.cget("text") + f" & PDF gespeichert: {os.path.basename(pdf_path)}", fg="green")
        except Exception as e:
            print(f"Fehler bei der PDF-Konvertierung: {e}")
            messagebox.showerror("PDF-Konvertierungsfehler", f"Fehler beim Konvertieren zu PDF: {e}")
            self.status_label.config(text=self.status_label.cget("text") + f" ❌ PDF-Konvertierungsfehler.", fg="red")

    # --- Listen- und Filterfunktionen ---
    def apply_filters(self, event=None):
        """Wird aufgerufen, wenn ein Filter geändert wird, und lädt die Liste neu."""
        self.load_invoices_to_listbox()

    def load_invoices_to_listbox(self):
        """Lädt alle Rechnungen aus der Datenbank in die Listbox, angewendet auf Filter."""
        self.invoice_listbox.delete(0, "end") # Vorherige Einträge löschen

        current_status_filter = self.status_filter_combobox.get()
        current_category_filter = self.category_combobox.get()

        invoices = get_invoices(current_status_filter, current_category_filter)
        self.invoice_data = {} # Speichert ID und vollständige Daten für Aktionen

        # Formatierung für die Listbox-Header: Anpassung der Breite für bessere Lesbarkeit
        header_format = "{:<5} {:<30} {:<10} {:<12} {:<15} {:<15} {:<10}"
        self.invoice_listbox.insert("end", header_format.format("ID", "Name", "Status", "Fällig", "Erinnerung", "Kategorie", "Erstellt"))
        self.invoice_listbox.insert("end", "-" * 110) # Trennlinie

        for invoice in invoices:
            # Das invoice-Tupel enthält jetzt auch den Kategorienamen (letztes Element durch LEFT JOIN)
            invoice_id, name, _, _, creation_date, status, due_date, reminder_date, category_id, category_name = invoice
            
            # Formatierung der Anzeige
            due_display = due_date if due_date else "N/A"
            reminder_display = reminder_date if reminder_date else "N/A"
            category_display = category_name if category_name else "Keine" # Wenn category_id NULL ist
            creation_display = creation_date.split(' ')[0] # Nur Datum, ohne Uhrzeit

            # Kürzen der Namen, falls zu lang
            display_name = (name[:28] + '..') if len(name) > 28 else name
            display_category = (category_display[:13] + '..') if len(category_display) > 13 else category_display

            display_text = header_format.format(
                invoice_id,
                display_name,
                status,
                due_display,
                reminder_display,
                display_category,
                creation_display
            )

            self.invoice_listbox.insert("end", display_text)
            self.invoice_data[display_text] = invoice # Speichern des gesamten Tupels (inkl. category_name)
    
    def on_invoice_double_click(self, event):
        """Öffnet die zugehörige PDF-Datei bei Doppelklick."""
        selected_indices = self.invoice_listbox.curselection()
        # Verhindert Aktionen auf dem Header oder der Trennlinie
        if not selected_indices or selected_indices[0] == 0 or selected_indices[0] == 1: 
            return

        selected_item_text = self.invoice_listbox.get(selected_indices[0])
        invoice_tuple = self.invoice_data.get(selected_item_text)

        if invoice_tuple:
            # pdf_path ist das 4. Element im Tupel (Index 3)
            pdf_path = invoice_tuple[3] 
            if pdf_path and os.path.exists(pdf_path):
                try:
                    # Plattformunabhängiges Öffnen der Datei
                    if os.name == 'nt':  # Windows
                        os.startfile(pdf_path)
                    elif os.uname().sysname == 'Darwin':  # macOS
                        subprocess.call(['open', pdf_path])
                    else:  # Linux
                        subprocess.call(['xdg-open', pdf_path])
                    self.status_label.config(text=f"Öffne PDF: {os.path.basename(pdf_path)}", fg="blue")
                except Exception as e:
                    messagebox.showerror("Fehler beim Öffnen", f"Konnte PDF nicht öffnen: {e}")
                    self.status_label.config(text="❌ Fehler beim Öffnen der PDF.", fg="red")
            else:
                messagebox.showwarning("PDF nicht gefunden", "Die zugehörige PDF-Datei existiert nicht mehr.")
                self.status_label.config(text="⚠️ PDF nicht gefunden.", fg="orange")

    # --- Rechnungsaktionen ---
    def get_selected_invoice_id(self):
        """Gibt die ID der aktuell ausgewählten Rechnung zurück."""
        selected_indices = self.invoice_listbox.curselection()
        if not selected_indices or selected_indices[0] == 0 or selected_indices[0] == 1: # Header oder Trennlinie nicht wählbar
            messagebox.showwarning("Keine Auswahl", "Bitte wählen Sie eine Rechnung aus der Liste aus.")
            return None
        
        selected_item_text = self.invoice_listbox.get(selected_indices[0])
        invoice_tuple = self.invoice_data.get(selected_item_text)
        
        if invoice_tuple:
            return invoice_tuple[0] # Die ID ist das erste Element im Tupel
        return None

    def update_selected_invoice_status(self, new_status):
        """Aktualisiert den Status der ausgewählten Rechnung."""
        invoice_id = self.get_selected_invoice_id()
        if invoice_id is not None:
            update_invoice_status(invoice_id, new_status)
            self.status_label.config(text=f"Status von Rechnung ID {invoice_id} auf '{new_status}' geändert.", fg="blue")
            self.load_invoices_to_listbox() # Liste aktualisieren

    def delete_selected_invoice(self):
        """Löscht die ausgewählte Rechnung aus der Datenbank und von der Festplatte."""
        invoice_id = self.get_selected_invoice_id()
        if invoice_id is not None:
            conn = sqlite3.connect('invoice_data.db')
            cursor = conn.cursor()
            # Pfade abrufen, bevor der DB-Eintrag gelöscht wird
            cursor.execute("SELECT image_path, pdf_path FROM invoices WHERE id = ?", (invoice_id,))
            paths = cursor.fetchone()
            conn.close()

            if messagebox.askyesno("Rechnung löschen", f"Sind Sie sicher, dass Sie Rechnung ID {invoice_id} löschen möchten? Dies kann nicht rückgängig gemacht werden."):
                delete_invoice(invoice_id)
                self.status_label.config(text=f"Rechnung ID {invoice_id} erfolgreich gelöscht.", fg="red")
                self.load_invoices_to_listbox() # Liste aktualisieren

                # Dateien von der Festplatte löschen
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
                self.status_label.config(text="Löschen abgebrochen.", fg="gray")
    
    # --- Erinnerungsfunktion ---
    def check_reminders_on_start(self):
        """Prüft beim Start auf fällige Rechnungen oder Erinnerungen."""
        today = datetime.now().strftime('%Y-%m-%d')
        conn = sqlite3.connect('invoice_data.db')
        cursor = conn.cursor()

        # Rechnungen, die heute fällig sind (und noch offen sind)
        cursor.execute("SELECT name, due_date FROM invoices WHERE due_date = ? AND status = 'Offen'", (today,))
        due_today = cursor.fetchall()

        # Rechnungen, deren Erinnerungsdatum heute ist
        cursor.execute("SELECT name, reminder_date FROM invoices WHERE reminder_date = ?", (today,))
        remind_today = cursor.fetchall()
        
        conn.close()

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
            self.status_label.config(text="Es gibt Benachrichtigungen für heute!", fg="orange")
        else:
            self.status_label.config(text="Keine aktuellen Benachrichtigungen.", fg="green")

    # --- Kategorienverwaltung ---
    def open_category_management(self):
        """Öffnet ein neues Fenster zur Verwaltung von Kategorien."""
        # Überprüfen, ob das Fenster bereits existiert und noch offen ist
        if hasattr(self, 'category_add_delete_window') and self.category_add_delete_window.winfo_exists():
            self.category_add_delete_window.lift() # Fenster in den Vordergrund bringen
            return

        self.category_add_delete_window = Toplevel(self)
        self.category_add_delete_window.title("Kategorien verwalten")
        self.category_add_delete_window.geometry("400x350")
        self.category_add_delete_window.transient(self) # Macht das Hauptfenster inaktiv
        self.category_add_delete_window.grab_set() # Fokus auf dieses Fenster

        frame = Frame(self.category_add_delete_window, padx=15, pady=15)
        frame.pack(fill="both", expand=True)

        # Neue Kategorie hinzufügen
        Label(frame, text="Neue Kategorie hinzufügen:", font=("Arial", 11, "bold")).pack(pady=5)
        self.new_category_entry = Entry(frame, font=("Arial", 10), width=30)
        self.new_category_entry.pack(pady=5)
        Button(frame, text="Hinzufügen", command=self.add_new_category, font=("Arial", 10)).pack(pady=5)

        # Bestehende Kategorien und löschen
        Label(frame, text="Bestehende Kategorien:", font=("Arial", 11, "bold")).pack(pady=10)
        
        category_list_frame = Frame(frame)
        category_list_frame.pack(fill="both", expand=True)

        self.category_listbox_add_delete = Listbox(category_list_frame, font=("Arial", 10), height=5, selectmode="single")
        self.category_listbox_add_delete.pack(side="left", fill="both", expand=True)
        
        cat_scrollbar = Scrollbar(category_list_frame, orient="vertical", command=self.category_listbox_add_delete.yview)
        cat_scrollbar.pack(side="right", fill="y")
        self.category_listbox_add_delete.config(yscrollcommand=cat_scrollbar.set)

        self.load_categories_for_management_listbox() # Lädt Kategorien in diese spezifische Listbox

        Button(frame, text="Ausgewählte Kategorie löschen", command=self.delete_selected_category, font=("Arial", 10), bg="#F44336", fg="white").pack(pady=10)

        # Wenn das Fenster geschlossen wird, den Fokus auf das Hauptfenster zurückgeben
        self.category_add_delete_window.protocol("WM_DELETE_WINDOW", self.on_category_window_close)

    def load_categories_for_management_listbox(self):
        """Lädt Kategorien in die Listbox im Kategorien-Verwaltungsfenster."""
        self.category_listbox_add_delete.delete(0, 'end')
        categories = get_categories()
        # Zeige nur die Namen an, sortiert
        for id, name in sorted(categories, key=lambda x: x[1]):
            self.category_listbox_add_delete.insert('end', name)

    def add_new_category(self):
        """Fügt eine neue Kategorie basierend auf der Eingabe hinzu."""
        new_cat_name = self.new_category_entry.get().strip()
        if new_cat_name:
            if add_category(new_cat_name):
                self.new_category_entry.delete(0, 'end')
                self.load_categories() # Aktualisiert Haupt-Dropdowns
                self.load_categories_for_management_listbox() # Aktualisiert Listbox im Management-Fenster
                self.status_label.config(text=f"Kategorie '{new_cat_name}' hinzugefügt.", fg="blue")
            else:
                self.status_label.config(text=f"Kategorie '{new_cat_name}' konnte nicht hinzugefügt werden.", fg="red")
        else:
            messagebox.showwarning("Eingabe fehlt", "Bitte geben Sie einen Namen für die neue Kategorie ein.")

    def delete_selected_category(self):
        """Löscht die ausgewählte Kategorie."""
        selected_indices = self.category_listbox_add_delete.curselection()
        if not selected_indices:
            messagebox.showwarning("Keine Auswahl", "Bitte wählen Sie eine Kategorie zum Löschen aus.")
            return

        selected_cat_name = self.category_listbox_add_delete.get(selected_indices[0])
        category_id_to_delete = self.categories_map.get(selected_cat_name) # Hole ID über den Namen

        if category_id_to_delete is not None:
            if messagebox.askyesno("Kategorie löschen", f"Sind Sie sicher, dass Sie die Kategorie '{selected_cat_name}' löschen möchten?\nAlle zugeordneten Rechnungen verlieren ihre Kategorie."):
                if delete_category(category_id_to_delete):
                    self.load_categories() # Aktualisiert Haupt-Dropdowns
                    self.load_categories_for_management_listbox() # Aktualisiert Listbox im Management-Fenster
                    self.status_label.config(text=f"Kategorie '{selected_cat_name}' gelöscht.", fg="red")
                    self.load_invoices_to_listbox() # Rechnungsliste neu laden, falls Kategorien geändert wurden
                else:
                    self.status_label.config(text=f"Fehler beim Löschen von Kategorie '{selected_cat_name}'.", fg="red")
        else:
            messagebox.showerror("Fehler", "Kategorie-ID konnte nicht gefunden werden.")

    def on_category_window_close(self):
        """Wird aufgerufen, wenn das Kategorien-Verwaltungsfenster geschlossen wird."""
        self.category_add_delete_window.grab_release()
        self.category_add_delete_window.destroy()
        self.load_invoices_to_listbox() # Stelle sicher, dass die Liste aktuell ist

# --- Start der Anwendung ---
if __name__ == '__main__':
    # Während der Entwicklung ist es hilfreich, die DB bei jeder großen Strukturänderung zu löschen.
    # In einer produktiven Anwendung würde man ALTER TABLE verwenden, um Daten zu erhalten.
    # Für einen sauberen Start bei Änderungen an der DB-Struktur:
    if os.path.exists('invoice_data.db'):
        os.remove('invoice_data.db')
        print("Alte Datenbank gelöscht, um neue Struktur zu erstellen.")

    app = InvoiceApp()
    app.mainloop()