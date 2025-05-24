import random
import re
import sqlite3
import tkinter as tk
from tkinter import messagebox, simpledialog, Toplevel, Listbox
from collections import Counter, defaultdict



class MealPlannerApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Plannificateur de mets hebdomadaire")
        self.root.geometry("800x880")
        self.meal_data = {day: [] for day in
                          ["Lundi", "Mardi", "Mercredi", "Jeudi", "Vendredi", "Samedi", "Dimanche"]}
        self.db_file = "./meals.db"
        self.setup_database()

        self.setup_ui()
        self.load_meals_from_db()



    class ScrollableFrame(tk.Frame):
        """A frame with vertical scrolling capability."""
        def __init__(self, parent, *args, **kwargs):
            super().__init__(parent, *args, **kwargs)

            self.canvas = tk.Canvas(self)
            self.canvas.pack(side="left", fill="both", expand=True)

            self.scrollbar = tk.Scrollbar(self, orient="vertical", command=self.canvas.yview)
            self.scrollbar.pack(side="right", fill="y")

            self.canvas.configure(yscrollcommand=self.scrollbar.set)

            self.inner_frame = tk.Frame(self.canvas)
            self.canvas.create_window((0, 0), window=self.inner_frame, anchor="nw")

            self.inner_frame.bind("<Configure>", lambda e: self.canvas.configure(scrollregion=self.canvas.bbox("all")))
            self.canvas.bind_all("<MouseWheel>", self._on_mousewheel)


        def _on_mousewheel(self, event):
            """Scroll vertically when the mouse wheel is used."""
            self.canvas.yview_scroll(-1 * (event.delta // 120), "units")



    def setup_database(self):
        """Ensures the database is initialized with the proper table."""
        conn = sqlite3.connect(self.db_file)
        cur = conn.cursor()
        cur.execute('''CREATE TABLE IF NOT EXISTS meals
            (name TEXT PRIMARY KEY,
            ingredients TEXT,
            preparation TEXT)''')
        cur.execute('''CREATE TABLE IF NOT EXISTS weekly_plan
            (day TEXT PRIMARY KEY,
            meals TEXT,
            leftovers INTEGER)''')
        cur.execute('''CREATE TABLE IF NOT EXISTS ingredient_category
            (ingredient TEXT PRIMARY KEY,
            category TEXT)''')
        cur.execute('''CREATE TABLE IF NOT EXISTS category_priority
            (priority INTEGER PRIMARY KEY,
            category TEXT)''')
        conn.commit()
        conn.close()


    def setup_ui(self):
        self.meal_frame = tk.Frame(self.root, bd=2, relief="groove", padx=10, pady=10)
        self.meal_frame.pack(side="left", fill="y", padx=10, pady=10)
        tk.Label(self.meal_frame, text="Gestion des mets", font=("Arial", 14)).pack()
        tk.Button(self.meal_frame, text="Ajouter un met", command=self.add_meal).pack(pady=5)
        tk.Button(self.meal_frame, text="Modifier un met", command=self.edit_meals).pack(pady=5)

        self.calendar_scrollable = self.ScrollableFrame(self.root)
        self.calendar_scrollable.pack(side="left", expand=True, fill="both", padx=10, pady=10)
        tk.Label(self.calendar_scrollable.inner_frame, text="Calendrier hebdomadaire", font=("Arial", 14)).pack()

        self.day_frames = {}
        for day in self.meal_data:
            day_frame = tk.Frame(self.calendar_scrollable.inner_frame, bd=1, relief="solid", padx=5, pady=5)
            day_frame.pack(fill="x", pady=5)

            tk.Label(day_frame, text=day, font=("Arial", 12)).pack(anchor="w")

            meal_list_frame = tk.Frame(day_frame)
            meal_list_frame.pack(side="left", fill="x", padx=5)
            self.day_frames[day] = meal_list_frame
            self.refresh_day(day)

        self.list_frame = tk.Frame(self.root, bd=2, relief="groove", padx=10, pady=10)
        self.list_frame.pack(side="left", fill="y", padx=10, pady=10)
        tk.Label(self.list_frame, text="Liste d'épicerie", font=("Arial", 14)).pack()
        tk.Button(self.list_frame, text="Générer la liste", command=self.generate_shopping_list).pack(pady=5)
        tk.Button(self.list_frame, text="Gérer la liste de priorité", command=self.manage_priority).pack(pady=5)
        tk.Button(self.meal_frame, text="Gérer les catégories", command=self.manage_categories).pack(pady=5)


    def open_weekly_calendar(self):
        """Opens the weekly calendar with scrollable functionality."""
        calendar_window = tk.Toplevel(self.root)
        calendar_window.title("Weekly Calendar")
        calendar_window.geometry("800x600")

        scrollable_frame = self.ScrollableFrame(calendar_window)
        scrollable_frame.pack(fill="both", expand=True, padx=10, pady=10)

        days_of_week = ["Lundi", "Mardi", "Mercredi", "Jeudi", "Vendredi", "Samedi", "Dimanche"]
        for day in days_of_week:
            day_frame = tk.Frame(scrollable_frame.inner_frame, bd=2, relief="groove", padx=10, pady=10)
            day_frame.pack(fill="x", pady=5)

            # Add content for the day
            tk.Label(day_frame, text=day, font=("Arial", 14)).pack(anchor="w")
            tk.Text(day_frame, height=5, width=70).pack(pady=5)


    def load_meals_from_db(self):
        """Loads planned meals and leftover status for the week from the database."""
        conn = sqlite3.connect(self.db_file)
        cur = conn.cursor()
        cur.execute("SELECT day, meals, leftovers FROM weekly_plan")
        rows = cur.fetchall()
        conn.close()
        for day, meals, leftovers in rows:
            if meals:
                meals_list = meals.split(",")
                leftovers_list = str(leftovers).split(",")
                self.meal_data[day] = list(zip(meals_list, leftovers_list))

        for day in self.meal_data:
            self.refresh_day(day)


    def fetch_meals_from_database(self):
        """Fetches all meals from the database."""
        conn = sqlite3.connect(self.db_file)
        cur = conn.cursor()
        cur.execute("SELECT name FROM meals")
        meals = [row[0] for row in cur.fetchall()]
        conn.close()
        return meals


    def fetch_meal_details(self, name):
        """Fetches details of a specific meal by name."""
        conn = sqlite3.connect(self.db_file)
        cur = conn.cursor()
        cur.execute("SELECT ingredients, preparation FROM meals WHERE name=?", (name,))
        result = cur.fetchone()
        conn.close()
        return result


    def add_meal(self):
        add_window = tk.Toplevel(self.root)
        add_window.title("Ajouter un met")

        tk.Label(add_window, text="Nom du met:").grid(row=0, column=0, padx=10, pady=5)
        meal_name_entry = tk.Entry(add_window)
        meal_name_entry.grid(row=0, column=1, padx=10, pady=5)

        tk.Label(add_window, text="Ingrédients (séparés par des virgules):").grid(row=1, column=0, padx=10, pady=5)
        ingredients_entry = tk.Entry(add_window)
        ingredients_entry.grid(row=1, column=1, padx=10, pady=5)

        tk.Label(add_window, text="Préparation:").grid(row=2, column=0, padx=10, pady=5)
        preparation_entry = tk.Text(add_window, height=5, width=30)
        preparation_entry.grid(row=2, column=1, padx=10, pady=5)


        def save_meal():
            name = meal_name_entry.get()
            ingredients = ingredients_entry.get()
            preparation = preparation_entry.get("1.0", "end").strip()
            db_file = "./meals.db"
            conn = sqlite3.connect(db_file)
            cur = conn.cursor()
            cur.execute(
                "INSERT into MEALS (name, ingredients, preparation) VALUES (?,?,?)",
                (name, ingredients, preparation)
            )
            conn.commit()
            conn.close()
            print(f"Saved: {name}, {ingredients}, {preparation}")
            add_window.destroy()

        tk.Button(add_window, text="Sauvegarder le met", command=save_meal).grid(row=3, column=0, columnspan=2, pady=10)


    def edit_meals(self):
        edit_window = tk.Toplevel(self.root)
        edit_window.title("Edit Meals")
        db_file = "./meals.db"
        conn = sqlite3.connect(db_file)
        cur = conn.cursor()
        cur.execute("SELECT name FROM meals")
        meals = cur.fetchall()
        conn.close()

        if not meals:
            tk.Label(edit_window, text="Aucun met sauvegardé!").pack(pady=10)
            return

        tk.Label(edit_window, text="Choisissez le met à modifier:", font=("Arial", 12)).pack(pady=5)

        for meal in meals:
            meal_name = meal[0]
            tk.Button(edit_window, text=meal_name,
                      command=lambda m=meal_name: self.edit_meal_details(m, edit_window)).pack(pady=2, fill="x")


    def edit_meal_details(self, meal_name, edit_window):
        db_file = "./meals.db"
        conn = sqlite3.connect(db_file)
        cur = conn.cursor()
        cur.execute("SELECT name, ingredients, preparation FROM meals WHERE name = ?", (meal_name,))
        meal_data = cur.fetchone()
        conn.close()

        if not meal_data:
            messagebox.showerror("Error", f"Meal '{meal_name}' not found!")
            return

        edit_detail_window = tk.Toplevel(edit_window)
        edit_detail_window.title(f"Modifier le met - {meal_name}")

        tk.Label(edit_detail_window, text="Nom du met:").grid(row=0, column=0, padx=10, pady=5)
        name_entry = tk.Entry(edit_detail_window)
        name_entry.grid(row=0, column=1, padx=10, pady=5)
        name_entry.insert(0, meal_data[0])  # Pre-fill with the existing name

        tk.Label(edit_detail_window, text="Ingrédients (séparés par virgule):").grid(row=1, column=0, padx=10, pady=5)
        ingredients_entry = tk.Entry(edit_detail_window)
        ingredients_entry.grid(row=1, column=1, padx=10, pady=5)
        ingredients_entry.insert(0, meal_data[1])  # Pre-fill with the existing ingredients

        tk.Label(edit_detail_window, text="Préparation:").grid(row=2, column=0, padx=10, pady=5)
        preparation_entry = tk.Text(edit_detail_window, height=5, width=30)
        preparation_entry.grid(row=2, column=1, padx=10, pady=5)
        preparation_entry.insert("1.0", meal_data[2])  # Pre-fill with the existing preparation


        def save_changes():
            new_name = name_entry.get()
            new_ingredients = ingredients_entry.get()
            new_preparation = preparation_entry.get("1.0", "end").strip()

            if not new_name or not new_ingredients or not new_preparation:
                messagebox.showwarning("Erreur de validation", "Tous les champs sont requis!")
                return

            conn = sqlite3.connect(db_file)
            cur = conn.cursor()
            try:
                cur.execute(
                    "UPDATE meals SET name = ?, ingredients = ?, preparation = ? WHERE name = ?",
                    (new_name, new_ingredients, new_preparation, meal_name)
                )
                conn.commit()
                messagebox.showinfo("Succès", "Le met a été mis à jour!")
                edit_detail_window.destroy()
                edit_window.destroy()
            except sqlite3.IntegrityError:
                messagebox.showerror("Erreur", "Le nom du met doit être unique!")
            finally:
                conn.close()

        tk.Button(
            edit_detail_window, text="Sauvegarder les changements", command=save_changes).grid(row=3, column=0, columnspan=2, pady=10
        )


    def edit_day_meals(self, day):
        edit_window = tk.Toplevel(self.root)
        edit_window.title(f"Gérer le met du {day}")
        edit_window.geometry("400x400")
        tk.Label(edit_window, text=f"Met pour {day}", font=("Arial", 14)).pack(pady=10)
        tk.Button(edit_window, text="Ajouter un met", command=lambda: self.add_meal_to_day(day, edit_window)).pack(pady=10)
        tk.Button(edit_window, text="Marquer comme restants",
                  command=lambda: self.add_leftover_to_day(day, edit_window)).pack(pady=10)


    def remove_meal_from_day(self, day, meal_name, is_leftover):
        """Removes a meal from the specified day."""
        if (meal_name, is_leftover) in self.meal_data[day]:
            self.meal_data[day].remove((meal_name, is_leftover))
            self.save_day_to_db(day)
            self.refresh_day(day)


    def save_day_to_db(self, day):
        """Saves the day's meals and leftovers to the database."""
        conn = sqlite3.connect(self.db_file)
        cur = conn.cursor()

        if self.meal_data[day]:
            meals = ",".join([meal[0] for meal in self.meal_data[day]])
            leftovers = ",".join([str(int(meal[1])) for meal in self.meal_data[day]])
            cur.execute('''
                INSERT INTO weekly_plan (day, meals, leftovers)
                VALUES (?, ?, ?)
                ON CONFLICT(day) DO UPDATE SET meals=excluded.meals, leftovers=excluded.leftovers
            ''', (day, meals, leftovers))
        else:
            cur.execute("DELETE FROM weekly_plan WHERE day=?", (day,))

        conn.commit()
        conn.close()


    def show_meal_card(self, meal_name):
        """Displays a window with the meal's ingredients and preparation."""
        details = self.fetch_meal_details(meal_name)
        if not details:
            messagebox.showerror("Erreur", f"Détails pour '{meal_name}' introuvables.")
            return

        ingredients, preparation = details

        meal_card_window = Toplevel(self.root)
        meal_card_window.title(f"Met: {meal_name}")
        meal_card_window.geometry("400x300")

        tk.Label(meal_card_window, text=meal_name, font=("Arial", 14)).pack(pady=10)
        list_ingredients = "\n".join(ingredient.strip() for ingredient in ingredients.split(","))

        tk.Label(meal_card_window, text="Ingrédients:", font=("Arial", 12)).pack(anchor="w", padx=10)
        tk.Label(meal_card_window, text=list_ingredients, font=("Arial", 10), wraplength=380, justify="left").pack(
            anchor="w", padx=10)

        tk.Label(meal_card_window, text="Préparation:", font=("Arial", 12)).pack(anchor="w", padx=10, pady=(10, 0))
        tk.Label(meal_card_window, text=preparation, font=("Arial", 10), wraplength=380, justify="left").pack(
            anchor="w", padx=10)


    def refresh_day(self, day):
        """Refreshes the display for a specific day."""
        for widget in self.day_frames[day].winfo_children():
            widget.destroy()

        for meal_name, is_leftover in self.meal_data[day]:
            frame = tk.Frame(self.day_frames[day])
            frame.pack(fill="x", pady=2)

            meal_button = tk.Button(
                frame, text=meal_name,
                command=lambda meal=meal_name: self.show_meal_card(meal),
                font=("Arial", 10)
            )
            meal_button.pack(side="left", padx=5)

            leftover_var = tk.BooleanVar(value=bool(int(is_leftover)))
            leftover_checkbox = tk.Checkbutton(
                frame, text="Restants", variable=leftover_var,
                command=lambda day=day, meal=meal_name, var=leftover_var: self.update_leftover_status(day, meal,
                                                                                                      var.get())
            )
            leftover_checkbox.pack(side="left", padx=5)

            remove_button = tk.Button(
                frame, text="Retirer",
                command=lambda meal=meal_name: self.remove_meal_from_day(day, meal, is_leftover)
            )
            remove_button.pack(side="right", padx=5)

        add_button = tk.Button(
            self.day_frames[day], text="Ajouter/Remplacer un met",
            command=lambda: self.select_meal_for_day(day),
            font=("Arial", 10)
        )
        add_button.pack(fill="x", pady=5)


    def update_leftover_status(self, day, meal_name, is_leftover):
        """Updates the leftover status for a specific meal on a specific day."""
        for i, (meal, leftover) in enumerate(self.meal_data[day]):
            if meal == meal_name:
                self.meal_data[day][i] = (meal_name, int(is_leftover))
                break
        self.save_day_to_db(day)


    def select_meal_for_day(self, day):
        """Opens a window to select or replace a meal for the specified day."""
        select_window = tk.Toplevel(self.root)
        select_window.title(f"Select Meal for {day}")

        meals = self.fetch_meals_from_database()

        for meal_name in meals:
            tk.Button(
                select_window, text=meal_name,
                command=lambda meal=meal_name: [self.add_meal_to_day(day, meal), select_window.destroy()]
            ).pack(fill="x", pady=2)


    def add_meal_to_day(self, day, meal_name, is_leftover=False):
        """Adds or replaces a meal for the specified day."""
        self.meal_data[day] = [(meal_name, is_leftover)]
        self.save_day_to_db(day)
        self.refresh_day(day)


    def generate_shopping_list(self):
        conn = sqlite3.connect(self.db_file)
        cur = conn.cursor()

        shopping_list = defaultdict(int)

        cur.execute("SELECT * FROM weekly_plan")
        weekly_plan = cur.fetchall()

        meals_in_calendar = []

        for row in weekly_plan:
            meals_column = row[1]
            if meals_column and row[2] != 1:
                meals = meals_column.split(",")
                meals_in_calendar.extend(meals)

        for meal_name in meals_in_calendar:
            cur.execute("SELECT ingredients FROM meals WHERE name = ?", (meal_name,))
            result = cur.fetchone()
            if result:
                ingredients = result[0].split(",")
                for ingredient in ingredients:
                    ingredient = ingredient.strip()
                    ingredient_clean = self.remove_quantity(ingredient)
                    ingredient_singular = self.get_singular_ingredient(ingredient_clean)
                    shopping_list[ingredient_singular] += 1

        categorized_ingredients = defaultdict(list)
        for ingredient in shopping_list:
            cur.execute("SELECT category FROM ingredient_category WHERE ingredient = ?", (ingredient,))
            result = cur.fetchone()
            if result:
                category = result[0]
            else:
                category = "Sans catégorie"

            categorized_ingredients[category].append((ingredient, shopping_list[ingredient]))
        conn.close()
        shopping_list_text = ""
        for category, ingredients in categorized_ingredients.items():
            shopping_list_text += f"\n{category.capitalize()}:\n"
            for ingredient, quantity in ingredients:
                shopping_list_text += f"  {ingredient} x{quantity}\n"

        self.display_shopping_list(shopping_list_text)


    def remove_quantity(self, ingredient):
        """
        Function to remove quantities from the ingredient (e.g., "3 cans of tomato soup" -> "tomato soup").
        """
        quantity_pattern = r"^\d+\s*(?:\w+\s*)*(?=\w)"
        ingredient_clean = re.sub(quantity_pattern, "", ingredient).strip()
        return ingredient_clean


    def get_singular_ingredient(self, ingredient):
        """
        Function to get the singular form of the ingredient (handles plural form detection).
        You can expand this function with more sophisticated plural handling if needed.
        """
        plural_rules = {
            's': '',
            'es': ''
        }
        for plural, singular in plural_rules.items():
            if ingredient.lower().endswith(plural):
                return ingredient[:-len(plural)] + singular

        return ingredient


    def display_shopping_list(self, shopping_list_text):
        shopping_list_window = tk.Toplevel(self.root)
        shopping_list_window.title("Liste d'épicerie")

        text_box = tk.Text(shopping_list_window, wrap=tk.WORD, height=20, width=50)
        text_box.insert(tk.END, shopping_list_text)
        text_box.config(state=tk.DISABLED)
        text_box.pack(padx=10, pady=10)

        tk.Button(shopping_list_window, text="Fermer", command=shopping_list_window.destroy).pack(pady=5)


    def get_ingredients_for_meal(self, meal_name):
        cur = self.conn.cursor()
        cur.execute('''SELECT ingredient FROM meal_ingredients WHERE meal_name = ?''', (meal_name,))
        ingredients = [row[0] for row in cur.fetchall()]
        return ingredients


    def manage_categories(self):
        """Opens a window to manage categories and their ingredients."""
        category_window = Toplevel(self.root)
        category_window.title("Gérer les catégories")
        category_window.geometry("600x600")

        scrollable_frame = self.ScrollableFrame(category_window)
        scrollable_frame.pack(fill="both", expand=True, padx=10, pady=10)

        conn = sqlite3.connect(self.db_file)
        cur = conn.cursor()
        cur.execute("SELECT DISTINCT category FROM ingredient_category")
        categories = [row[0] for row in cur.fetchall()]
        conn.close()

        for category in categories:
            self.create_category_ui(scrollable_frame.inner_frame, category)

        tk.Button(
            scrollable_frame.inner_frame,
            text="Ajouter une nouvelle catégorie",
            command=lambda: self.add_new_category(scrollable_frame.inner_frame)
        ).pack(pady=10)


    def create_category_ui(self, parent_frame, category):
        """Creates a UI section for an existing category."""
        frame = tk.Frame(parent_frame, bd=2, relief="groove", padx=10, pady=10)
        frame.pack(fill="x", pady=5)

        tk.Label(frame, text=f"Catégorie: {category}", font=("Arial", 12)).pack(anchor="w", pady=5)

        conn = sqlite3.connect(self.db_file)
        cur = conn.cursor()
        cur.execute("SELECT ingredient FROM ingredient_category WHERE category=?", (category,))
        ingredients = [row[0] for row in cur.fetchall()]
        conn.close()

        text_frame = tk.Frame(frame)
        text_frame.pack(fill="x", pady=5)

        scrollbar = tk.Scrollbar(text_frame, orient="vertical")
        scrollbar.pack(side="right", fill="y")

        ingredient_textbox = tk.Text(text_frame, height=5, font=("Arial", 10), yscrollcommand=scrollbar.set,
                                     wrap="word")
        ingredient_textbox.insert("1.0", ", ".join(ingredients))  # Pre-fill with current ingredients
        ingredient_textbox.pack(side="left", fill="both", expand=True)
        scrollbar.config(command=ingredient_textbox.yview)

        btn_frame = tk.Frame(frame)
        btn_frame.pack(fill="x", pady=5)
        tk.Button(btn_frame, text="Sauvegarder",
                  command=lambda: self.save_ingredients_from_textbox(category, ingredient_textbox)).pack(side="left",
                                                                                                         padx=5)
        tk.Button(btn_frame, text="Supprimer", command=lambda: self.delete_category(frame, category)).pack(side="left",
                                                                                                        padx=5)


    def delete_category(self, frame, category):
        """Deletes a category and updates the UI."""
        if messagebox.askyesno(
            "Confirmer la suppression",
            f"Êtes-vous sur de vouloir supprimer la catégorie '{category}'?"
        ):
            conn = sqlite3.connect(self.db_file)
            cur = conn.cursor()
            cur.execute("DELETE FROM ingredient_category WHERE category=?", (category,))
            conn.commit()
            cur.execute("DELETE FROM category_priority WHERE category=?", (category,))
            conn.commit()
            conn.close()

            frame.destroy()
            messagebox.showinfo("Succès", f"La catégorie '{category}' a été supprimée.")


    def save_ingredients_from_textbox(self, category, ingredient_textbox):
        """Saves all ingredients for a category from a textbox."""
        ingredients = ingredient_textbox.get("1.0", "end").strip()
        if not ingredients:
            messagebox.showerror("Erreur", "Le champ ingrédient est vide.")
            return

        conn = sqlite3.connect(self.db_file)
        cur = conn.cursor()

        cur.execute("DELETE FROM ingredient_category WHERE category=?", (category,))

        for ingredient in ingredients.split(","):
            cur.execute("INSERT INTO ingredient_category (ingredient, category) VALUES (?, ?)",
                        (ingredient.strip(), category))
        conn.commit()
        conn.close()

        messagebox.showinfo("Succès", f"Les ingrédients pour la catégorie '{category}' ont été mis à jour.")


    def add_new_category(self, parent_frame):
        """Adds a new category."""
        new_category_frame = tk.Frame(parent_frame, bd=2, relief="groove", padx=5, pady=5)
        new_category_frame.pack(fill="x", pady=5)
        tk.Entry(new_category_frame, width=30).pack(side="left", padx=5)
        tk.Button(new_category_frame, text="Supprimer", command=lambda: new_category_frame.destroy()).pack(side="left",
                                                                                                           padx=5)
        new_category = simpledialog.askstring("Nouvelle catégorie", "Entrez le nom de la nouvelle catégorie:")
        if not new_category:
            return

        conn = sqlite3.connect(self.db_file)
        cur = conn.cursor()
        cur.execute("SELECT DISTINCT category FROM ingredient_category WHERE category=?", (new_category,))
        if cur.fetchone():
            conn.close()
            messagebox.showerror("Erreur", f"La catégorie '{new_category}' existe déjà.")
            return
        conn.close()

        self.create_category_ui(parent_frame, new_category)


    def manage_priority(self):
        priority_window = tk.Toplevel(self.root)
        priority_window.title("Gérer la liste de priorité")
        priority_window.geometry("600x400")

        left_frame = tk.Frame(priority_window)
        left_frame.pack(side="left", fill="both", expand=True, padx=10, pady=10)
        tk.Label(left_frame, text="Non assignées", font=("Arial", 12)).pack()
        unassigned_listbox = tk.Listbox(left_frame, selectmode="single", height=15)
        unassigned_listbox.pack(fill="both", expand=True)

        right_frame = tk.Frame(priority_window)
        right_frame.pack(side="right", fill="both", expand=True, padx=10, pady=10)
        tk.Label(right_frame, text="Priorité", font=("Arial", 12)).pack()
        priority_listbox = tk.Listbox(right_frame, selectmode="single", height=15)
        priority_listbox.pack(fill="both", expand=True)

        self.load_category_lists(unassigned_listbox, priority_listbox)

        button_frame = tk.Frame(priority_window)
        button_frame.pack(fill="x", pady=10)
        tk.Button(button_frame, text=">>",
                  command=lambda: self.move_category(unassigned_listbox, priority_listbox)).pack(side="top", padx=5,
                                                                                                 pady=5)
        tk.Button(button_frame, text="<<",
                  command=lambda: self.move_category(priority_listbox, unassigned_listbox)).pack(side="top", padx=5,
                                                                                                 pady=5)

        tk.Button(priority_window, text="Enregistrer",
                  command=lambda: self.save_priority_list(priority_listbox, unassigned_listbox)).pack(pady=10)


    def load_category_lists(self, unassigned_listbox, priority_listbox):
        conn = sqlite3.connect(self.db_file)
        cur = conn.cursor()
        cur.execute("SELECT category FROM category_priority ORDER BY priority")
        assigned_categories = [row[0] for row in cur.fetchall()]

        cur.execute("SELECT DISTINCT category FROM ingredient_category")
        all_categories = [row[0] for row in cur.fetchall()]
        conn.close()
        unassigned_categories = [cat for cat in all_categories if cat not in assigned_categories]

        for category in assigned_categories:
            priority_listbox.insert("end", category)
        for category in unassigned_categories:
            unassigned_listbox.insert("end", category)


    def move_category(self, from_listbox, to_listbox):
        selected_index = from_listbox.curselection()
        if selected_index:
            category = from_listbox.get(selected_index)
            from_listbox.delete(selected_index)
            to_listbox.insert("end", category)


    def save_priority_list(self, priority_listbox, unassigned_listbox):
        ordered_categories = priority_listbox.get(0, "end")
        categories_with_priority = [(i + 1, category) for i, category in enumerate(ordered_categories)]
        unassigned_categories = unassigned_listbox.get(0, "end")
        unassigned_with_priority = [(random.randint(50, 999), category) for category in unassigned_categories]
        conn = sqlite3.connect(self.db_file)
        cur = conn.cursor()
        cur.execute("DELETE FROM category_priority")
        for priority, category in categories_with_priority + unassigned_with_priority:
            cur.execute("INSERT INTO category_priority (priority, category) VALUES (?, ?)", (priority, category))
        conn.commit()
        conn.close()


    def get_ingredients_by_category(self, category):
        conn = sqlite3.connect(self.db_file)
        cur = conn.cursor()
        cur.execute('''SELECT ingredient FROM ingredient_category WHERE category = ?''', (category,))
        ingredients = [row[0] for row in cur.fetchall()]
        conn.close()
        return ingredients


    def normalize_ingredient(self, ingredient):
        """
        Normalize ingredient names by applying regex to match common plural forms
        or variations, e.g., 'onionS' -> 'onion', 'tomatos' -> 'tomato'.
        """
        plural_patterns = {
            r"s$": ""
        }
        for pattern, replacement in plural_patterns.items():
            if re.search(pattern, ingredient):
                ingredient = re.sub(pattern, replacement, ingredient)
                break

        return ingredient



if __name__ == "__main__":
    root = tk.Tk()
    app = MealPlannerApp(root)
    root.mainloop()
