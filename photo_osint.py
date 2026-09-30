"""
IMAGE EXIF & GPS RECON TOOL (AZOD814)
Forensic Metadata Extractor & Geolocation Tracer

Educational & Cyber Security Awareness Use Only.
"""

import os
import sys
import webbrowser
import tkinter as tk
from tkinter import filedialog, messagebox
from datetime import datetime
from PIL import Image, ImageTk
from PIL.ExifTags import TAGS, GPSTAGS
import folium

# --- TKINTER DRAG & DROP SUPPORT ---
DND_AVAILABLE = False
try:
    from tkinterdnd2 import DND_FILES, TkinterDnD
    TkRoot = TkinterDnD.Tk
    DND_AVAILABLE = True
except ImportError:
    TkRoot = tk.Tk

# --- TACTICAL DARK THEME ---
BG = "#0a0e14"
BG_CARD = "#121820"
BG_PANEL = "#18222d"
BORDER = "#253342"
ACCENT_CYAN = "#00e5ff"
ACCENT_GREEN = "#10b981"
ACCENT_WARN = "#f59e0b"
ACCENT_RED = "#ef4444"
TEXT_WHITE = "#f8fafc"
TEXT_MUTED = "#8699af"
INPUT_BG = "#06090d"

FONT_MAIN = "Segoe UI" if os.name == "nt" else "DejaVu Sans"
FONT_MONO = "Consolas" if os.name == "nt" else "DejaVu Sans Mono"


def ensure_dirs():
    for d in ("reports", "maps"):
        os.makedirs(d, exist_ok=True)


def convert_to_degrees(value):
    """Convert GPS coordinates from EXIF format (degrees, minutes, seconds) to decimal."""
    try:
        d = float(value[0])
        m = float(value[1])
        s = float(value[2])
        return d + (m / 60.0) + (s / 3600.0)
    except Exception:
        return None


class PhotoReconApp:
    def __init__(self, root):
        self.root = root
        self.root.title("EXIF RECON // GEOLOCATION OSINT TOOL")
        self.root.geometry("1400x860")
        self.root.minsize(980, 640)
        self.root.configure(bg=BG)

        self.current_image_path = None
        self.extracted_gps = None
        self.extracted_data = {}
        self.preview_image = None

        ensure_dirs()
        self.build_ui()

    def build_ui(self):
        # 1. Top Navbar
        nav = tk.Frame(self.root, bg=BG_CARD, height=72, highlightthickness=1, highlightbackground=BORDER)
        nav.pack(fill="x", padx=14, pady=(12, 8))
        nav.pack_propagate(False)

        brand = tk.Frame(nav, bg=BG_CARD)
        brand.pack(side="left", padx=18)
        tk.Label(brand, text="◈  IMAGE EXIF & GPS RECON", fg=ACCENT_CYAN, bg=BG_CARD, font=(FONT_MAIN, 14, "bold")).pack(anchor="w")
        tk.Label(brand, text="METADATA FORENSICS & GEOLOCATION TRACER", fg=TEXT_MUTED, bg=BG_CARD, font=(FONT_MAIN, 8)).pack(anchor="w")

        status_box = tk.Frame(nav, bg=BG_CARD)
        status_box.pack(side="right", padx=18)
        self.status_lbl = tk.Label(status_box, text="● ENGINE READY", fg=ACCENT_GREEN, bg=BG_CARD, font=(FONT_MONO, 10, "bold"))
        self.status_lbl.pack(anchor="e")
        self.status_sub = tk.Label(status_box, text="STANDBY", fg=TEXT_MUTED, bg=BG_CARD, font=(FONT_MONO, 8))
        self.status_sub.pack(anchor="e")

        # 2. Main Workspace (2 Columns)
        body = tk.Frame(self.root, bg=BG)
        body.pack(fill="both", expand=True, padx=14, pady=4)
        body.grid_columnconfigure(0, weight=3)
        body.grid_columnconfigure(1, weight=2)
        body.grid_rowconfigure(0, weight=1)

        # LEFT COLUMN (Dropzone, Controls & GPS Card)
        left_col = tk.Frame(body, bg=BG)
        left_col.grid(row=0, column=0, sticky="nsew", padx=(0, 8))

        # Drag and Drop Target Area
        self.drop_card = tk.Frame(left_col, bg=BG_CARD, highlightthickness=2, highlightbackground=BORDER)
        self.drop_card.pack(fill="x", pady=(0, 8))

        self.drop_inner = tk.Frame(self.drop_card, bg=INPUT_BG, height=140)
        self.drop_inner.pack(fill="x", padx=8, pady=8)
        self.drop_inner.pack_propagate(False)

        tk.Label(self.drop_inner, text="⇪", fg=ACCENT_CYAN, bg=INPUT_BG, font=(FONT_MAIN, 26)).pack(pady=(12, 2))
        self.drop_label = tk.Label(
            self.drop_inner,
            text="DRAG & DROP IMAGE FILE HERE\n(OR CLICK 'BROWSE FILE' BELOW)",
            fg=TEXT_WHITE, bg=INPUT_BG, font=(FONT_MONO, 9, "bold"), justify="center"
        )
        self.drop_label.pack()

        # Drag & Drop Binding
        if DND_AVAILABLE:
            try:
                self.drop_card.drop_target_register(DND_FILES)
                self.drop_card.dnd_bind("<<Drop>>", self.on_file_drop)
                self.drop_inner.drop_target_register(DND_FILES)
                self.drop_inner.dnd_bind("<<Drop>>", self.on_file_drop)
            except Exception:
                pass

        # Control Row
        btn_bar = tk.Frame(left_col, bg=BG)
        btn_bar.pack(fill="x", pady=(0, 8))

        tk.Button(
            btn_bar, text="📁  SELECT IMAGE FILE", command=self.browse_file,
            bg="#0284c7", fg="#ffffff", activebackground="#0369a1", font=(FONT_MAIN, 8, "bold"),
            relief="flat", padx=16, pady=8, cursor="hand2"
        ).pack(side="left", fill="x", expand=True, padx=(0, 4))

        self.map_btn = tk.Button(
            btn_bar, text="🗺  OPEN SATELLITE MAP", command=self.open_interactive_map,
            bg="#166534", fg="#ffffff", activebackground="#15803d", font=(FONT_MAIN, 8, "bold"),
            relief="flat", padx=16, pady=8, cursor="hand2", state="disabled"
        )
        self.map_btn.pack(side="left", fill="x", expand=True, padx=(4, 0))

        # Geolocation Card
        geo_card = tk.Frame(left_col, bg=BG_CARD, highlightthickness=1, highlightbackground=BORDER)
        geo_card.pack(fill="x", pady=(0, 8))

        tk.Label(geo_card, text="📍  GEOLOCATION & GPS COORDINATES", fg=ACCENT_CYAN, bg=BG_CARD, font=(FONT_MAIN, 9, "bold")).pack(anchor="w", padx=14, pady=(10, 4))
        self.geo_text = tk.Label(
            geo_card,
            text="GPS STATUS: NO TARGET LOADED\nExact coordinates, altitude, and timestamps will populate here.",
            fg=TEXT_MUTED, bg=BG_CARD, font=(FONT_MONO, 8), justify="left", anchor="w"
        )
        self.geo_text.pack(fill="x", padx=14, pady=(0, 10))

        # Metadata Table
        data_card = tk.Frame(left_col, bg=BG_CARD, highlightthickness=1, highlightbackground=BORDER)
        data_card.pack(fill="both", expand=True)

        tk.Label(data_card, text="EXIF FORENSIC METADATA ATTRIBUTES", fg=ACCENT_CYAN, bg=BG_CARD, font=(FONT_MAIN, 9, "bold")).pack(anchor="w", padx=14, pady=(10, 6))

        scroll_wrap = tk.Frame(data_card, bg=BG_CARD)
        scroll_wrap.pack(fill="both", expand=True, padx=12, pady=(0, 10))

        self.table_canvas = tk.Canvas(scroll_wrap, bg=BG_CARD, highlightthickness=0)
        sbar = ttk.Scrollbar(scroll_wrap, orient="vertical", command=self.table_canvas.yview)
        self.table_inner = tk.Frame(self.table_canvas, bg=BG_CARD)

        self.table_inner.bind("<Configure>", lambda e: self.table_canvas.configure(scrollregion=self.table_canvas.bbox("all")))
        self.table_win = self.table_canvas.create_window((0, 0), window=self.table_inner, anchor="nw")
        self.table_canvas.bind("<Configure>", lambda e: self.table_canvas.itemconfigure(self.table_win, width=e.width))
        self.table_canvas.configure(yscrollcommand=sbar.set)

        self.table_canvas.pack(side="left", fill="both", expand=True)
        sbar.pack(side="right", fill="y")

        self.render_empty_table()

        # RIGHT COLUMN (Visual Inspection & Forensic Console)
        right_col = tk.Frame(body, bg=BG)
        right_col.grid(row=0, column=1, sticky="nsew")

        # Preview Container
        img_card = tk.Frame(right_col, bg=BG_CARD, highlightthickness=1, highlightbackground=BORDER)
        img_card.pack(fill="x", pady=(0, 8))

        tk.Label(img_card, text="IMAGE VISUAL INSPECTION", fg=ACCENT_CYAN, bg=BG_CARD, font=(FONT_MAIN, 9, "bold")).pack(anchor="w", padx=14, pady=(10, 6))

        self.canvas_preview = tk.Canvas(img_card, bg=INPUT_BG, height=270, highlightthickness=0)
        self.canvas_preview.pack(fill="x", padx=12, pady=(0, 6))
        self.img_caption = tk.Label(img_card, text="No target image loaded", fg=TEXT_MUTED, bg=BG_CARD, font=(FONT_MAIN, 8))
        self.img_caption.pack(pady=(0, 8))
        self.draw_placeholder()

        # Export Actions
        act_card = tk.Frame(right_col, bg=BG_CARD, highlightthickness=1, highlightbackground=BORDER)
        act_card.pack(fill="x", pady=(0, 8))
        tk.Label(act_card, text="FORENSIC ACTIONS", fg=ACCENT_CYAN, bg=BG_CARD, font=(FONT_MAIN, 9, "bold")).pack(anchor="w", padx=14, pady=(10, 6))

        btn_row = tk.Frame(act_card, bg=BG_CARD)
        btn_row.pack(fill="x", padx=12, pady=(0, 10))

        tk.Button(btn_row, text="📋  COPY ALL EXIF DATA", command=self.copy_metadata, bg=BG_PANEL, fg=TEXT_WHITE, font=(FONT_MAIN, 8, "bold"), relief="flat", bd=1, highlightbackground=BORDER, pady=6, cursor="hand2").pack(fill="x", pady=2)
        tk.Button(btn_row, text="💾  EXPORT JSON REPORT", command=self.export_json_report, bg=BG_PANEL, fg=TEXT_WHITE, font=(FONT_MAIN, 8, "bold"), relief="flat", bd=1, highlightbackground=BORDER, pady=6, cursor="hand2").pack(fill="x", pady=2)

        # Activity Telemetry Log
        log_card = tk.Frame(right_col, bg=BG_CARD, highlightthickness=1, highlightbackground=BORDER)
        log_card.pack(fill="both", expand=True)

        tk.Label(log_card, text="FORENSIC ACTIVITY LOGS", fg=ACCENT_CYAN, bg=BG_CARD, font=(FONT_MAIN, 9, "bold")).pack(anchor="w", padx=14, pady=(8, 4))
        self.log_text = tk.Text(log_card, bg=INPUT_BG, fg=TEXT_MUTED, font=(FONT_MONO, 7), relief="flat", bd=0)
        self.log_text.pack(fill="both", expand=True, padx=10, pady=(0, 10))
        self.log_msg("EXIF Engine initialized.")

    def render_empty_table(self):
        for w in self.table_inner.winfo_children():
            w.destroy()

        fields = [
            "CAMERA MAKE", "CAMERA MODEL", "DATE & TIME TAKEN",
            "SHUTTER SPEED", "APERTURE (F-NUMBER)", "ISO SPEED",
            "FOCAL LENGTH", "IMAGE RESOLUTION", "SOFTWARE / OS",
            "GPS LATITUDE", "GPS LONGITUDE", "ALTITUDE"
        ]
        self.row_labels = {}
        for f in fields:
            row = tk.Frame(self.table_inner, bg=BG_CARD)
            row.pack(fill="x", pady=2)
            tk.Label(row, text=f, fg=TEXT_MUTED, bg=BG_CARD, font=(FONT_MAIN, 7, "bold"), width=22, anchor="w").pack(side="left", padx=8)
            lbl = tk.Label(row, text="--", fg=TEXT_WHITE, bg=INPUT_BG, font=(FONT_MONO, 8), anchor="w", padx=8, pady=4, wraplength=440, justify="left")
            lbl.pack(side="left", fill="x", expand=True)
            self.row_labels[f] = lbl

    def draw_placeholder(self):
        self.canvas_preview.delete("all")
        w = max(self.canvas_preview.winfo_width(), 260)
        h = max(self.canvas_preview.winfo_height(), 220)
        self.canvas_preview.create_rectangle(15, 15, w - 15, h - 15, outline=BORDER, width=1)
        self.canvas_preview.create_text(w // 2, h // 2, text="[ NO IMAGE PREVIEW AVAILABLE ]", fill=TEXT_MUTED, font=(FONT_MAIN, 8))

    def log_msg(self, msg):
        self.log_text.insert("end", f"[{datetime.now():%H:%M:%S}] {msg}\n")
        self.log_text.see("end")

    # --- FILE SELECTION & EXTRACTION ---
    def browse_file(self):
        path = filedialog.askopenfilename(
            title="Select Image File",
            filetypes=[("Image Files", "*.jpg *.jpeg *.png *.tiff *.webp"), ("All Files", "*.*")]
        )
        if path:
            self.process_image(path)

    def on_file_drop(self, event):
        path = event.data.strip()
        # Clean path for Windows curly braces
        if path.startswith("{") and path.endswith("}"):
            path = path[1:-1]
        if os.path.isfile(path):
            self.process_image(path)

    def process_image(self, path):
        self.current_image_path = path
        filename = os.path.basename(path)
        self.drop_label.config(text=f"LOADED:\n{filename}")
        self.status_lbl.config(text="● ANALYZING", fg=ACCENT_WARN)
        self.log_msg(f"Target selected: {filename}")

        # Render visual preview immediately
        self.render_image_preview(path)

        # Extract metadata
        threading.Thread(target=self._metadata_worker, args=(path,), daemon=True).start()

    def render_image_preview(self, path):
        try:
            with Image.open(path) as img:
                img = img.convert("RGB")
                w = max(self.canvas_preview.winfo_width(), 260)
                h = max(self.canvas_preview.winfo_height(), 220)
                img.thumbnail((w - 20, h - 20), Image.Resampling.LANCZOS)
                self.preview_image = ImageTk.PhotoImage(img)

            self.canvas_preview.delete("all")
            self.canvas_preview.create_image(w // 2, h // 2, image=self.preview_image, anchor="center")
            self.img_caption.config(text=os.path.basename(path)[:40], fg=ACCENT_CYAN)
        except Exception as e:
            self.draw_placeholder()
            self.log_msg(f"Preview render error: {e}")

    def _metadata_worker(self, path):
        metadata = {}
        gps_info = {}

        try:
            with Image.open(path) as img:
                metadata["IMAGE RESOLUTION"] = f"{img.width} x {img.height} Pixels"
                metadata["FORMAT"] = img.format

                exif_raw = img._getexif()
                if exif_raw:
                    for tag_id, value in exif_raw.items():
                        tag_name = TAGS.get(tag_id, str(tag_id))
                        if tag_name == "GPSInfo":
                            for gps_id in value:
                                sub_name = GPSTAGS.get(gps_id, str(gps_id))
                                gps_info[sub_name] = value[gps_id]
                        else:
                            metadata[tag_name] = value
        except Exception as e:
            self.log_msg(f"EXIF parsing error: {e}")

        # Parse GPS
        lat, lon = None, None
        if gps_info:
            try:
                lat_raw = gps_info.get("GPSLatitude")
                lat_ref = gps_info.get("GPSLatitudeRef", "N")
                lon_raw = gps_info.get("GPSLongitude")
                lon_ref = gps_info.get("GPSLongitudeRef", "E")

                if lat_raw and lon_raw:
                    lat = convert_to_degrees(lat_raw)
                    if lat_ref == "S":
                        lat = -lat

                    lon = convert_to_degrees(lon_raw)
                    if lon_ref == "W":
                        lon = -lon
            except Exception as e:
                self.log_msg(f"GPS parsing error: {e}")

        self.root.after(0, lambda: self.render_metadata_results(metadata, gps_info, lat, lon))

    def render_metadata_results(self, meta, gps_raw, lat, lon):
        self.status_lbl.config(text="● ANALYSIS COMPLETE", fg=ACCENT_GREEN)
        self.extracted_data = meta
        self.extracted_gps = (lat, lon) if (lat and lon) else None

        # Helper to safely search
        def get_val(*keys):
            for k in keys:
                for mk, v in meta.items():
                    if k.lower() == mk.lower() and v:
                        return str(v).strip()
            return "N/A"

        # Populate Fields
        self.row_labels["CAMERA MAKE"].config(text=get_val("Make"))
        self.row_labels["CAMERA MODEL"].config(text=get_val("Model"))
        self.row_labels["DATE & TIME TAKEN"].config(text=get_val("DateTimeOriginal", "DateTime"))
        self.row_labels["SHUTTER SPEED"].config(text=get_val("ExposureTime", "ShutterSpeedValue"))
        self.row_labels["APERTURE (F-NUMBER)"].config(text=get_val("FNumber", "ApertureValue"))
        self.row_labels["ISO SPEED"].config(text=get_val("ISOSpeedRatings", "ISO"))
        self.row_labels["FOCAL LENGTH"].config(text=get_val("FocalLength"))
        self.row_labels["IMAGE RESOLUTION"].config(text=meta.get("IMAGE RESOLUTION", "N/A"))
        self.row_labels["SOFTWARE / OS"].config(text=get_val("Software"))

        # GPS Population
        if lat and lon:
            self.row_labels["GPS LATITUDE"].config(text=f"{lat:.6f}")
            self.row_labels["GPS LONGITUDE"].config(text=f"{lon:.6f}")
            self.row_labels["ALTITUDE"].config(text=f"{gps_raw.get('GPSAltitude', 'N/A')} m")

            self.geo_text.config(
                text=f"LATITUDE  : {lat:.6f}\nLONGITUDE : {lon:.6f}\nMAP LINK  : Google Maps Coordinates Ready\nSTATUS    : GEOLOCATION LOCKED",
                fg=ACCENT_GREEN
            )
            self.map_btn.config(state="normal")
            self.log_msg(f"Geolocation extracted: {lat:.6f}, {lon:.6f}")
        else:
            self.row_labels["GPS LATITUDE"].config(text="NO GPS DATA")
            self.row_labels["GPS LONGITUDE"].config(text="NO GPS DATA")
            self.row_labels["ALTITUDE"].config(text="N/A")

            self.geo_text.config(
                text="GPS STATUS: NO COORDINATES FOUND IN FILE\n"
                     "(Note: Compressed social media photos strip GPS data. "
                     "Original camera/document photos retain full coordinates.)",
                fg=ACCENT_WARN
            )
            self.map_btn.config(state="disabled")
            self.log_msg("No GPS tag present in EXIF.")

    # --- SATELLITE MAP GENERATOR ---
    def open_interactive_map(self):
        if not self.extracted_gps:
            return

        lat, lon = self.extracted_gps
        map_path = os.path.abspath("maps/target_geolocation.html")

        # Folium interactive map
        m = folium.Map(location=[lat, lon], zoom_start=17, tiles="OpenStreetMap")
        
        # Add high-precision target pin
        popup_html = f"""
        <div style="font-family:sans-serif;font-size:12px;">
            <b>Target Image Geolocation</b><br>
            <b>Lat:</b> {lat:.6f}<br>
            <b>Lon:</b> {lon:.6f}<br>
            <a href="https://www.google.com/maps/search/?api=1&query={lat},{lon}" target="_blank">Open in Google Maps</a>
        </div>
        """
        folium.Marker(
            [lat, lon],
            popup=folium.Popup(popup_html, max_width=300),
            icon=folium.Icon(color="red", icon="crosshairs", prefix="fa")
        ).add_to(m)

        m.save(map_path)
        self.log_msg(f"Generated interactive map: {map_path}")
        webbrowser.open(f"file://{map_path}")

    # --- EXPORT ACTIONS ---
    def copy_metadata(self):
        if not self.extracted_data:
            ModernDialog(self.root, "NO DATA", "Analyze an image first.")
            return

        lines = [f"IMAGE FORENSIC DOSSIER: {os.path.basename(self.current_image_path or '')}"]
        lines.append("=" * 60)
        for k, v in self.extracted_data.items():
            lines.append(f"{k}: {v}")
        if self.extracted_gps:
            lines.append(f"GPS COORDINATES: {self.extracted_gps[0]}, {self.extracted_gps[1]}")

        self.root.clipboard_clear()
        self.root.clipboard_append("\n".join(lines))
        self.log_msg("EXIF data copied to clipboard.")
        ModernDialog(self.root, "COPIED", "All metadata attributes copied to clipboard!", accent=ACCENT_GREEN)

    def export_json_report(self):
        if not self.extracted_data:
            ModernDialog(self.root, "NO DATA", "Analyze an image first.")
            return

        payload = {
            "target_file": self.current_image_path,
            "timestamp": str(datetime.now()),
            "coordinates": self.extracted_gps,
            "exif": {str(k): str(v) for k, v in self.extracted_data.items()}
        }

        fn = filedialog.asksaveasfilename(
            defaultextension=".json",
            initialfile="exif_recon_report.json",
            filetypes=[("JSON files", "*.json")]
        )
        if fn:
            with open(fn, "w", encoding="utf-8") as f:
                json.dump(payload, f, indent=2)
            self.log_msg(f"Exported JSON dossier to {fn}")


def main():
    root = TkRoot()
    app = PhotoReconApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
