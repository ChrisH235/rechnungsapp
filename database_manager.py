import sqlite3
from datetime import datetime

class DatabaseManager:
    def __init__(self, db_path="invoice_data.db"):
        self.conn = sqlite3.connect(db_path)
        self.cursor = self.conn.cursor()
        self._create_tables()

    def _create_tables(self):
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS categories (
                id INTEGER PRIMARY KEY,
                name TEXT UNIQUE NOT NULL
            )
        ''')
        # HINWEIS: Die Spalte 'amount' wurde hinzugefügt
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS invoices (
                id INTEGER PRIMARY KEY,
                name TEXT NOT NULL,
                amount REAL,
                image_path TEXT,
                pdf_path TEXT,
                creation_date TEXT,
                status TEXT NOT NULL,
                due_date TEXT,
                reminder_date TEXT,
                tax_declaration_year INTEGER,
                category_id INTEGER,
                FOREIGN KEY (category_id) REFERENCES categories (id)
            )
        ''')
        self.conn.commit()

    def add_category(self, name):
        try:
            self.cursor.execute("INSERT INTO categories (name) VALUES (?)", (name,))
            self.conn.commit()
            return True
        except sqlite3.IntegrityError:
            return False

    def get_categories(self):
        self.cursor.execute("SELECT id, name FROM categories ORDER BY name")
        return self.cursor.fetchall()
    
    def delete_category(self, category_id):
        try:
            self.cursor.execute("UPDATE invoices SET category_id = NULL WHERE category_id = ?", (category_id,))
            self.cursor.execute("DELETE FROM categories WHERE id = ?", (category_id,))
            self.conn.commit()
            return True
        except sqlite3.Error as e:
            print(f"Fehler beim Löschen der Kategorie: {e}")
            return False

    # HINWEIS: Die Funktion erwartet jetzt 8 Argumente (plus 'self')
    def add_invoice(self, name, amount, image_path, pdf_path, status, due_date, reminder_date, category_id):
        self.cursor.execute('''
            INSERT INTO invoices (name, amount, image_path, pdf_path, status, due_date, reminder_date, creation_date, category_id)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (name, amount, image_path, pdf_path, status, due_date, reminder_date, datetime.now().strftime('%Y-%m-%d %H:%M:%S'), category_id))
        self.conn.commit()
        return True

    def get_invoices(self, status_filter="Alle", category_filter="Alle", tax_filter=False):
        query = "SELECT i.id, i.name, i.amount, i.image_path, i.pdf_path, i.creation_date, i.status, i.due_date, i.reminder_date, i.tax_declaration_year, c.name FROM invoices i LEFT JOIN categories c ON i.category_id = c.id WHERE 1=1"
        params = []
        if status_filter != "Alle":
            query += " AND i.status = ?"
            params.append(status_filter)
        if category_filter != "Alle":
            query += " AND c.name = ?"
            params.append(category_filter)
        if tax_filter:
            query += " AND i.tax_declaration_year IS NOT NULL"
        
        query += " ORDER BY i.due_date DESC"
        
        self.cursor.execute(query, params)
        return self.cursor.fetchall()
    
    def update_invoice_status(self, invoice_id, new_status):
        self.cursor.execute("UPDATE invoices SET status = ? WHERE id = ?", (new_status, invoice_id))
        self.conn.commit()
        return True
    
    def get_due_and_reminder_invoices(self, today):
        due_query = "SELECT name, due_date FROM invoices WHERE due_date = ? AND status = 'Offen'"
        self.cursor.execute(due_query, (today,))
        due_invoices = self.cursor.fetchall()
        
        reminder_query = "SELECT name, reminder_date FROM invoices WHERE reminder_date = ? AND status != 'Bezahlt'"
        self.cursor.execute(reminder_query, (today,))
        reminder_invoices = self.cursor.fetchall()
        
        return due_invoices, reminder_invoices
    
    def delete_invoice(self, invoice_id):
        self.cursor.execute("DELETE FROM invoices WHERE id = ?", (invoice_id,))
        self.conn.commit()
        return True
    
    def get_invoice_paths(self, invoice_id):
        self.cursor.execute("SELECT image_path, pdf_path FROM invoices WHERE id = ?", (invoice_id,))
        return self.cursor.fetchone()
    
    def set_invoice_for_tax_declaration(self, invoice_id, year):
        self.cursor.execute("UPDATE invoices SET tax_declaration_year = ? WHERE id = ?", (year, invoice_id))
        self.conn.commit()
        return True
        
    def get_total_amount_by_category(self):
        self.cursor.execute('''
            SELECT c.name, SUM(i.amount)
            FROM invoices i
            JOIN categories c ON i.category_id = c.id
            WHERE i.amount IS NOT NULL
            GROUP BY c.name
            ORDER BY SUM(i.amount) DESC
        ''')
        return self.cursor.fetchall()

    def __del__(self):
        self.conn.close()