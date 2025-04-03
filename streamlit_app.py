# streamlit_app.py
import streamlit as st
import pandas as pd
from PIL import Image, ImageDraw, ImageFont
import io
import os
import zipfile
from datetime import datetime
from pathlib import Path
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email import encoders
import smtplib

from drive_utils import read_excel_from_drive, read_csv_from_drive, write_df_to_drive

# Google Drive File IDs
STUDENTS_FILE_ID = "1Rx2InNQuj5GNAOICOzrsi6wdvEcuMrqR"
LOG_FILE_ID = "1Yw0g1MJGpvJDa3rJExmMXoZ0jpDvogZk"

LOCAL_SAVE_DIR = Path("submitted_photos")
LOCAL_SAVE_DIR.mkdir(exist_ok=True)

if "submitted_files" not in st.session_state:
    st.session_state["submitted_files"] = []

def send_email_with_zip(to_email, subject, body, zip_bytes, filename="photos.zip"):
    try:
        smtp_host = "smtp.gmail.com"
        smtp_port = 587
        sender_email = "ramchand2009@gmail.com"
        email_password = "jtpy hhin rqcn tmvn"

        msg = MIMEMultipart()
        msg["From"] = sender_email
        msg["To"] = to_email
        msg["Subject"] = subject
        msg.attach(MIMEText(body, "plain"))

        mime_part = MIMEBase("application", "zip")
        mime_part.set_payload(zip_bytes)
        encoders.encode_base64(mime_part)
        mime_part.add_header("Content-Disposition", f"attachment; filename=\"{filename}\"")
        msg.attach(mime_part)

        with smtplib.SMTP(smtp_host, smtp_port) as server:
            server.starttls()
            server.login(sender_email, email_password)
            server.send_message(msg)

        st.success(" Email sent successfully!")

    except Exception as e:
        st.error(f" Failed to send email: {e}")

def login():
    st.title("Volunteer Login")
    username = st.text_input("Volunteer Name")
    password = st.text_input("Password", type="password")

    df = read_excel_from_drive(STUDENTS_FILE_ID)
    valid_users = df["Volunteer_Name"].dropna().unique().tolist()

    if st.button("Login"):
        if username in valid_users and password == username:
            st.session_state["logged_in"] = True
            st.session_state["username"] = username
            st.rerun()
        else:
            st.error("Invalid username or password.")

if "logged_in" not in st.session_state:
    st.session_state["logged_in"] = False

if not st.session_state["logged_in"]:
    login()
    st.stop()

st.set_page_config(page_title="Agaram 2025 HV Photo Sender", layout="centered")
st.title(" Agaram 2025 HV Photo Email Sender")

st.sidebar.markdown(f" Logged in as: **{st.session_state['username']}**")
if st.sidebar.button(" Logout"):
    st.session_state.clear()
    st.rerun()

# Load and filter students
students_df = read_excel_from_drive(STUDENTS_FILE_ID)
students_df = students_df[students_df["Volunteer_Name"] == st.session_state["username"]]

try:
    st.sidebar.subheader(" My Students")
    st.sidebar.dataframe(
        students_df[["Student_ID", "Student_Name", "Volunteer_Name","Status"]],
        use_container_width=True
    )
except Exception as e:
    st.sidebar.error(f"Error displaying students: {e}")

font_size = st.slider("Font Size", min_value=10, max_value=100, value=100)

student_names = students_df["Student_Name"].tolist()
selected_name = st.selectbox("Select a student", student_names)
student_row = students_df[students_df["Student_Name"] == selected_name].iloc[0]
student_id = student_row["Student_ID"]
volunteer_name = student_row.get("Volunteer_Name", "")
district = student_row.get("District", "")

photos = st.file_uploader(
    f"Upload Photos for {selected_name}",
    type=["jpg", "jpeg", "png"],
    accept_multiple_files=True,
    key=f"uploader_{student_id}"
)

if st.button(" Reset Uploads"):
    st.rerun()

if photos:
    st.info("Click 'Submit' below each image to process it individually.")
    for j, photo in enumerate(photos):
        angle_key = f"angle_{student_id}_{j}"
        if angle_key not in st.session_state:
            st.session_state[angle_key] = 0

        col1, col2, col3 = st.columns([4, 1, 1])
        with col1:
            st.session_state[angle_key] = st.slider(
                f" Rotate '{photo.name}'", 0, 360, st.session_state[angle_key], step=90, key=f"slider_{student_id}_{j}"
            )
        with col2:
            #if st.button( key=f"rotate_left_{student_id}_{j}"):
            if st.button("↩️", key=f"rotate_left_{student_id}_{j}"):

                st.session_state[angle_key] = (st.session_state[angle_key] - 90) % 360
        with col3:
            #if st.button( key=f"rotate_right_{student_id}_{j}"):
            if st.button("↪️", key=f"rotate_right_{student_id}_{j}"):

                st.session_state[angle_key] = (st.session_state[angle_key] + 90) % 360

        image = Image.open(photo).convert("RGBA")
        rotated = image.rotate(st.session_state[angle_key], expand=True)
        txt_layer = Image.new("RGBA", rotated.size, (255, 255, 255, 0))
        draw = ImageDraw.Draw(txt_layer)

        try:
            font = ImageFont.truetype("arial.ttf", font_size)
        except:
            font = ImageFont.load_default()

        x, y = 10, 10
        line_spacing = font_size + 10
        draw.text((x, y), f"Student_ID: {student_id}", font=font, fill=(255, 0, 0, 150)); y += line_spacing
        draw.text((x, y), f"Student_Name: {selected_name}", font=font, fill=(255, 0, 0, 150)); y += line_spacing
        draw.text((x, y), f"Volunteer_Name: {volunteer_name}", font=font, fill=(255, 0, 0, 150))

        final_image = Image.alpha_composite(rotated, txt_layer).convert("RGB")
        st.image(final_image, caption=f"Watermarked Preview: {photo.name}", use_container_width=True)

        if st.button(f" Submit {photo.name}", key=f"submit_{student_id}_{j}"):
            file_name = f"{student_id}_{selected_name}_{j+1}.jpg"
            local_file_path = LOCAL_SAVE_DIR / file_name
            final_image.save(local_file_path)
            st.session_state["submitted_files"].append(local_file_path)

            try:
                log_df = read_csv_from_drive(LOG_FILE_ID)
            except:
                log_df = pd.DataFrame(columns=["Student_ID", "Student_Name", "Photo_Name", "Status", "Timestamp"])

            new_entry = pd.DataFrame([{
                "Student_ID": student_id,
                "Student_Name": selected_name,
                "Photo_Name": file_name,
                "Status": "Submitted",
                "Timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            }])

            log_df = pd.concat([log_df, new_entry], ignore_index=True)
            write_df_to_drive(log_df, LOG_FILE_ID, file_type="csv")

            st.success(f" {file_name} submitted successfully.")

st.subheader(" Submission Status")
try:
    logs = read_csv_from_drive(LOG_FILE_ID)
    student_logs = logs[logs["Student_ID"] == student_id]
    if not student_logs.empty:
        st.dataframe(student_logs[["Photo_Name", "Status", "Timestamp"]].sort_values("Timestamp", ascending=False))
    else:
        st.info("No submissions yet for this student.")
except:
    st.info("No logs found.")

# Create and send ZIP
st.subheader(" Submitted Photos ZIP")
if st.session_state["submitted_files"]:
    zip_filename = f"{student_id}_{selected_name}_{district}.zip"
    zip_buffer = io.BytesIO()

    with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zipf:
        for file_path in st.session_state["submitted_files"]:
            with open(file_path, "rb") as f:
                zipf.writestr(Path(file_path).name, f.read())
    zip_buffer.seek(0)

    st.download_button(
        label=" Download ZIP File",
        data=zip_buffer,
        file_name=zip_filename,
        mime="application/zip"
    )

    if st.button("Send Email with Submitted Photos"):
        send_email_with_zip(
            to_email="ramchandv2024@gmail.com",
            subject="Student Photos Submission",
            body=f"Attached are the submitted photos for {selected_name} ({student_id}) from {district}.",
            zip_bytes=zip_buffer.getvalue(),
            filename=zip_filename
        )
        students_df.loc[students_df["Student_ID"] == student_id, "Status"] = "Email Sent"
        write_df_to_drive(students_df, STUDENTS_FILE_ID, file_type="excel")
else:
    st.info("No submitted photos found to download or email.")
