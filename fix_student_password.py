import hashlib
import sqlite3

def fix_student_password(student_id, new_password):
    """Fix student password by updating database with hashed password"""
    hashed_password = hashlib.sha256(new_password.encode()).hexdigest()
    
    conn = sqlite3.connect('students.db')
    cursor = conn.cursor()
    
    cursor.execute("UPDATE students SET password = ? WHERE student_id = ?", 
                   (hashed_password, student_id))
    conn.commit()
    conn.close()
    
    return f"Password updated for student {student_id}"

if __name__ == "__main__":
    student_id = input("Enter student ID: ")
    new_password = input("Enter new password: ")
    result = fix_student_password(student_id, new_password)
    print(result)