import sqlite3, datetime
from flask import Flask, render_template, request, redirect, url_for
import plotly.express as px
import plotly.io as pio
import plotly.graph_objects as go

app = Flask(__name__)

class Habit:
    # Class variables initiator
    def __init__(self, db_name="habits.db"):
        self.db_name = db_name
        self._create_tables()

    # Create the database 
    def _create_tables(self):
        con = sqlite3.connect(self.db_name)
        db = con.cursor()
        db.execute("""
            CREATE TABLE IF NOT EXISTS habits (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL UNIQUE,
                description TEXT,
                created_date DATE NOT NULL
            )
        """)
        db.execute("""
            CREATE TABLE IF NOT EXISTS habit_tracker (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                habit_id INTEGER NOT NULL,
                date DATE NOT NULL,
                UNIQUE (habit_id, date),
                FOREIGN KEY (habit_id) REFERENCES habits(id) ON DELETE CASCADE
            )
        """)
        con.commit()
        con.close()
    # add habit method
    def add(self, name, desc):
        con = sqlite3.connect(self.db_name)
        db = con.cursor()
        created_date = str(datetime.date.today())
        db.execute("INSERT INTO habits (name, description, created_date) VALUES (?, ?, ?)",
                   (name, desc, created_date))
        con.commit()
        con.close()

    # delete habit method
    def delete(self, habit_id):
        con = sqlite3.connect(self.db_name)
        db = con.cursor()
        try:
            # First delete related tracker entries
            db.execute("DELETE FROM habit_tracker WHERE habit_id = ?", (habit_id,))
            # Then delete the habit
            db.execute("DELETE FROM habits WHERE id = ?", (habit_id,))
            con.commit()
            print(f"Successfully deleted habit {habit_id}")
        except Exception as e:
            print(f"Error deleting habit: {e}")
            con.rollback()
        finally:
            con.close()

    # mark as done method
    def mark(self, habit_id, date=None):
        if not date:
            date = str(datetime.date.today())
        con = sqlite3.connect(self.db_name)
        db = con.cursor()
        db.execute("INSERT OR IGNORE INTO habit_tracker (habit_id, date) VALUES (?, ?)",
                   (habit_id, date))
        con.commit()
        con.close()

    # unmark method
    def unmark(self, habit_id, date=None):
        if not date:
            date = str(datetime.date.today())
        con = sqlite3.connect(self.db_name)
        db = con.cursor()
        db.execute("DELETE FROM habit_tracker WHERE habit_id = ? AND date = ?",
                   (habit_id, date))
        con.commit()
        con.close()

    # Full Query 
    def get_all(self):
        con = sqlite3.connect(self.db_name)
        con.row_factory = sqlite3.Row  # 👈 this makes rows act like dicts
        db = con.cursor()
        db.execute("SELECT h.* , count(t.id) as total_done from habits h left join habit_tracker t on h.id = t.habit_id group by h.id  ")
        habits = db.fetchall()
        con.close()
        return habits

    # Streak calculator method
    def streak(self,habit_id):
        today = datetime.date.today()
        streak = 0
        con = sqlite3.connect(self.db_name)
        db = con.cursor()
        streakrows = db.execute("select date from habit_tracker where habit_id = ? order by date DESC", (habit_id,))

        for row in streakrows.fetchall():
            completed_date = datetime.date.fromisoformat(row[0])
            if completed_date == today - datetime.timedelta(days=streak):
                streak += 1
            else:
                break
        return streak
    
    # Visualization ( Bar Chart ) method
    def generate_chart(self):

        # Connect to database
        con = sqlite3.connect("habits.db")
        con.row_factory = sqlite3.Row
        db = con.cursor()

        # Query habits + how many times they were done
        db.execute("""
            SELECT h.*, COUNT(t.id) AS total_done
            FROM habits h
            LEFT JOIN habit_tracker t ON h.id = t.habit_id
            GROUP BY h.id
        """)
        habits = db.fetchall()

        # Prepare data for chart
        categories = []
        values = []
        for row in habits:
            habit = dict(row)
            categories.append(habit["name"])
            values.append(habit["total_done"])

        # Making the chart
        fig = px.bar(
            x=categories, 
            y=values, 
            title="Habit Tracker Progress",
            labels={"x": "Habit", "y": "Times Completed"},  # axis labels
            text=values  # show numbers on bars
        )
        fig.update_traces(textposition="outside", marker_color="#111827")  # style

        fig.update_layout(
            plot_bgcolor="#0a0d12",
            paper_bgcolor="#0a0d12",
            font=dict(size=14, family="Courier New", color="white"),
            title=dict(x=0.5, font=dict(size=22, color="#03DAC6")),
            xaxis=dict(showgrid=False,color="white", showline=True, linecolor="white"),
            yaxis=dict(showgrid=False,color="white", showline=True, linecolor="white", gridcolor="#444444")
        )
        # saving the chart as png
        pio.write_image(fig, "static/dashboard.png", width=1200, height=600, scale=2)

    # Heat map visualization method
    def habit_chart(self, habit_id):

        # Connect to database
        con = sqlite3.connect("habits.db")
        con.row_factory = sqlite3.Row
        db = con.cursor()

        # Query dates 
        db.execute("""
            SELECT date from habit_tracker
            where habit_id = ?
            order by date
        """, (habit_id,))

        dates = db.fetchall()

        # Prepare data for chart
        marked_done = []
        full_timeline = []
        for row in dates:
            marked_done.append(row['date'])

        today = datetime.date.today()
        k = today - datetime.timedelta(days=90)
        current_date = k
        while current_date <= today:
            current_date_str = current_date.strftime('%Y-%m-%d')
            if current_date_str in marked_done:
                status = 1
            else:
                status = 0
            full_timeline.append({'date' : current_date, 'status' : status})
            current_date += datetime.timedelta(days=1)

        # into weeks
        week_data = []
        for i in range(0, len(full_timeline),7):
            week = []
            for j in range(7):
                if i + j < len(full_timeline):
                    week.append(full_timeline[i + j] ['status'])
                else:
                    week.append(0)
            week_data.append(week)        
            
        # transpose
        days_data = []
        for day in range(7):
            days_across = []
            for week in week_data:
                days_across.append(week[day])
            days_data.append(days_across)
        day_labels = ['Saturday' , 'Sunday' , 'Monday' , 'Tuesday' , 'Wednesday' , 'Thursday' , 'Friday']
        fig = go.Figure(data=go.Heatmap(
        z=days_data,
        x=list(range(len(week_data))),
        y=day_labels,
        colorscale=[[0, '#161b22'], [1, '#39d353']],
        showscale=False,
        hovertemplate='Week: %{x}<br>Day: %{y}<br>Completed: %{z}<extra></extra>',
        xgap=2,
        ygap=2
        ))

        # make the heat map
        fig.update_layout(
        title=f"Habit Progress (Last 90 days)",
        plot_bgcolor="#0a0d12",
        paper_bgcolor="#0a0d12",
        font=dict(
            family="-apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif", 
            color="#c9d1d9"
        ),
        title_font=dict(size=20, color="#58a6ff"),
        width=1000,
        height=200,
        margin=dict(l=80, r=40, t=60, b=40),
        xaxis=dict(
            showgrid=False,
            showline=False,
            zeroline=False,
            color="#8b949e",
            tickfont=dict(size=10),
            side='top',
            tickmode='array',
            tickvals=list(range(len(week_data))),  # [0, 1, 2, 3, 4, ...]
            ticktext=[str(i) for i in range(len(week_data))]# ["0", "1", "2", ...]
        ),
        yaxis=dict(
            showgrid=False,
            showline=False,
            zeroline=False,
            tickfont=dict(size=10),
            color="#8b949e"
        ),
        xaxis_title="",
        yaxis_title=""
        )
    
        # Save it as png
        pio.write_image(fig, "static/habit_chart.png", width=1200, height=600, scale=2)
        


# Creating new Object
habit_manager = Habit()

# ---------------- ROUTES ---------------- #

@app.route("/")
def index():
    habit_rows = habit_manager.get_all()


    habits = []
    for row in habit_rows:
        habit = dict(row)  
        habit['streak'] = habit_manager.streak(habit['id'])
        habits.append(habit)

    return render_template("index.html", habits=habits)

@app.route("/add", methods=["POST"])
def add():
    name = request.form["name"]
    desc = request.form["description"]
    habit_manager.add(name, desc)
    return redirect(url_for("index"))

@app.route("/delete/<int:habit_id>", methods=["POST"])
def delete(habit_id):
    try:
        habit_manager.delete(habit_id)
        return redirect(url_for("index"))
    except Exception as e:
        print(f"Flask route error: {e}")
        return "Error deleting habit", 500

@app.route("/mark/<int:habit_id>", methods=["POST"])
def mark(habit_id):
    habit_manager.mark(habit_id)
    return redirect(url_for("index"))

@app.route("/unmark/<int:habit_id>", methods=["POST"])
def unmark(habit_id):
    habit_manager.unmark(habit_id)
    return redirect(url_for("index"))

@app.route("/streak/<int:habit_id>")
def streak(habit_id):
    habit_manager.streak(habit_id)
    return redirect(url_for("index"))

@app.route("/dashboard/")
def dashboard():
    habits = habit_manager.get_all()
    if habits :

        habit_manager.generate_chart()
        
    else:
        pass
    return render_template('dashboard.html', habits=habits)

@app.route("/habit/<int:habit_id>/chart")
def habit_chart(habit_id):

    habit_manager.habit_chart(habit_id)
    return render_template('habit_chart.html')

if __name__ == "__main__":
    app.run(debug=True)
