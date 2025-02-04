# **Big Cat Vocalization Management System**  

## **📌 Project Description**  
This is a **Django-based web application** designed for **analyzing and visualizing big cat vocalizations**. It allows **admins** to upload audio files and **staff** to visualize spectrograms and waveforms to analyze vocal patterns.  

---

## **🚀 Features**  
- **User Authentication & Role-Based Access** (Admin & Staff)  
- **Secure Role-Based Access Control (RBAC)**
- **Audio Upload & Processing Pipeline(TBD)**  
- **Spectrogram & Waveform Visualization(TBD)**  
- **Database Storage for Processed Clips(TBD)**  

---

## **🛠️ System Requirements**  
Make sure you have the following installed:  
- **Python** (Version 3.8 or later)  
- **Git**  
- **Django** (Version 5.1.2)  
- **SQLite3** (Comes with Django)  
- **Virtual Environment (venv)**  

---

## **📥 Installation Steps**  

### **1️⃣ Clone the Repository**  
Open a terminal and run:  

```sh
git clone https://github.com/yourusername/Big-Cat-Vocalization.git
cd Big-Cat-Vocalization
```

---

### **2️⃣ Create & Activate Virtual Environment**  

```sh
# Create a virtual environment
python -m venv venv

# Activate it (For Windows)
venv\Scripts\activate

# Activate it (For Mac/Linux)
source venv/bin/activate
```

---

### **3️⃣ Install Dependencies**  
Install all required Python packages using:  

```sh
pip install -r requirements.txt
```

---

### **4️⃣ Apply Migrations & Create Database**  
Run the following commands to set up the database:  

```sh
python manage.py makemigrations
python manage.py migrate
```

---

### **5️⃣ Create a Superuser**  
To access the **admin panel**, create a superuser:  

```sh
python manage.py createsuperuser
```
- Enter **email, username, and password** when prompted.  

---

### **6️⃣ Run the Development Server**  
Start the Django application by running:  

```sh
python manage.py runserver
```

- Open your browser and go to **`http://127.0.0.1:8000/`**  

---

## **🔑 Default User Roles & Access**  
- **Admin**  
  - Can upload audio files  
  - Manage staff users  
  - View and analyze audio data  

- **Staff**  
  - Can only visualize spectrograms & waveforms  
  - Can review audio analysis  

---

## **🔧 Common Issues & Fixes**  

### **1️⃣ Database Errors**  
If you encounter database errors, delete the existing database and run migrations again:  

```sh
rm db.sqlite3  # Linux/Mac
del db.sqlite3  # Windows

python manage.py migrate
```

---

### **2️⃣ Static Files Not Loading?**  
Run the following command:  

```sh
python manage.py collectstatic --noinput
```
