import matplotlib.pyplot as plt

class DataAnalytics:
    def __init__(self, db_manager):
        self.db_manager = db_manager

    def display_all_charts(self):
        self.display_spending_by_category()
        
    def display_spending_by_category(self):
        data = self.db_manager.get_total_amount_by_category()
        if not data:
            self.show_no_data_message("Keine Ausgabendaten verfügbar.")
            return

        categories = [item[0] for item in data]
        amounts = [item[1] for item in data]

        fig, ax = plt.subplots(figsize=(10, 6))
        
        # Erstelle ein Bar-Chart mit den Ausgaben pro Kategorie
        ax.bar(categories, amounts, color='#4CAF50')

        ax.set_title('Gesamtausgaben pro Kategorie', fontsize=16)
        ax.set_xlabel('Kategorie', fontsize=12)
        ax.set_ylabel('Gesamtausgaben in €', fontsize=12)
        plt.xticks(rotation=45, ha="right")
        plt.tight_layout()
        plt.show()

    def show_no_data_message(self, message):
        fig, ax = plt.subplots(figsize=(10, 6))
        ax.text(0.5, 0.5, message, ha='center', va='center', fontsize=14)
        ax.axis('off')
        plt.show()