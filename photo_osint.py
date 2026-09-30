"""
IMAGE EXIF & GPS RECON TOOL (AZOD814) - v2.0
Tactical Geolocation OSINT with Embedded In-App Interactive Map

Educational & Cyber Security Awareness Use Only.
"""

import os
import sys
import json
import threading
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from datetime import datetime
from PIL import Image, ImageTk
from PIL.ExifTags import TAGS, GPSTAGS

# Embedded Interactive Map inside Tkinter (Free, Zero API Key)
try:
    import tkintermapview
    MAP_AVAILABLE = True
except ImportError:
    MAP_AVAILABLE = False

# Native Drag and drop support
DND_AVAILABLE = False
try:
    from tkinterdnd2 import DND_FILES, TkinterDnD
    TkRoot = TkinterDnD.Tk
    DND_AVAILABLE = True
except ImportError:
    TkRoot = tk.Tk


# Tactical Slate Palette
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

FONT_MAIN = "DejaVu Sans" if os.name != "nt" else "Segoe UI"
FONT_MONO = "DejaVu Sans Mono" if os.name != "nt" else "Consolas"


def ensure_dirs():
    for d in ("reports", "cache"):
        os.makedirs(d, exist_ok=True)


def convert_to_degrees(value):
    """Convert GPS coordinates from EXIF format (degrees, minutes, seconds) to decimal."""
    try:
        def val_to_float(v):
            if hasattr(v, 'numerator') and hasattr(v, 'denominator'):
                return float(v.numerator) / float(v.denominator) if v.denominator != 0 else float(v.numerator)
            return float(v)

        d = val_to_float(value[0])
        m = val_to_float(value[1])
        s = val_to_float(value[2])
        return d + (m / 60.0) + (s / 3600.0)
    except Exception:
        return None


class PhotoReconApp:
    def __init__(self, root):
        self.root = root
        self.root.title("EXIF RECON // GEOLOCATION OSINT TOOL")
        self.root.geometry("1480x900")
        self.root.minsize(1050, 680)
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
        tk.Label(brand, text="EMBEDDED SATELLITE RADAR & METADATA FORENSICS", fg=TEXT_MUTED, bg=BG_CARD, font=(FONT_MAIN, 8)).pack(anchor="w")

        status_box = tk.Frame(nav, bg=BG_CARD)
        status_box.pack(side="right", padx=18)
        self.status_lbl = tk.Label(status_box, text="● ENGINE READY", fg=ACCENT_GREEN, bg=BG_CARD, font=(FONT_MONO, 10, "bold"))
        self.status_lbl.pack(anchor="e")
        self.status_sub = tk.Label(status_box, text="STANDBY", fg=TEXT_MUTED, bg=BG_CARD, font=(FONT_MONO, 8))
        self.status_sub.pack(anchor="e")

        # 2. Main Two-Column Structure
        body = tk.Frame(self.root, bg=BG)
        body.pack(fill="both", expand=True, padx=14, pady=4)
        body.grid_columnconfigure(0, weight=1)
        body.grid_columnconfigure(1, weight=1)
        body.grid_rowconfigure(0, weight=1)

        # LEFT COLUMN (Dropzone, Controls & Full Forensic Data)
        left_col = tk.Frame(body, bg=BG)
        left_col.grid(row=0, column=0, sticky="nsew", padx=(0, 8))

        # Drag and Drop Area
        self.drop_card = tk.Frame(left_col, bg=BG_CARD, highlightthickness=2, highlightbackground=BORDER)
        self.drop_card.pack(fill="x", pady=(0, 8))

        self.drop_inner = tk.Frame(self.drop_card, bg=INPUT_BG, height=130)
        self.drop_inner.pack(fill="x", padx=8, pady=8)
        self.drop_inner.pack_propagate(False)

        tk.Label(self.drop_inner, text="⇪", fg=ACCENT_CYAN, bg=INPUT_BG, font=(FONT_MAIN, 24)).pack(pady=(8, 0))
        self.drop_label = tk.Label(
            self.drop_inner,
            text="DRAG & DROP IMAGE FILE HERE\nOR CLICK 'SELECT IMAGE FILE' BELOW",
            fg=TEXT_WHITE, bg=INPUT_BG, font=(FONT_MONO, 9, "bold"), justify="center"
        )
        self.drop_label.pack(pady=(4, 8))

        # Linux/Windows Multi-Handler Drop Binding
        if DND_AVAILABLE:
            for widget in (self.drop_card, self.drop_inner, self.drop_label):
                widget.drop_target_register(DND_FILES)
                widget.dnd_bind("<<Drop>>", self.on_file_drop)

        # File Select Button
        btn_bar = tk.Frame(left_col, bg=BG)
        btn_bar.pack(fill="x", pady=(0, 8))

        tk.Button(
            btn_bar, text="📁  SELECT IMAGE FILE", command=self.browse_file,
            bg="#0284c7", fg="#ffffff", activebackground="#0369a1", font=(FONT_MAIN, 8, "bold"),
            relief="flat", padx=16, pady=8, cursor="hand2"
        ).pack(side="left", fill="x", expand=True, padx=(0, 4))

        tk.Button(
            btn_bar, text="📋  COPY EXIF DATA", command=self.copy_metadata,
            bg=BG_PANEL, fg=TEXT_WHITE, activebackground=BORDER, font=(FONT_MAIN, 8, "bold"),
            relief="flat", padx=16, pady=8, cursor="hand2"
        ).pack(side="left", fill="x", expand=True, padx=(4, 0))

        # Geolocation Card
        geo_card = tk.Frame(left_col, bg=BG_CARD, highlightthickness=1, highlightbackground=BORDER)
        geo_card.pack(fill="x", pady=(0, 8))

        tk.Label(geo_card, text="📍  GEOLOCATION & RADAR LOCK", fg=ACCENT_CYAN, bg=BG_CARD, font=(FONT_MAIN, 9, "bold")).pack(anchor="w", padx=14, pady=(8, 2))
        self.geo_text = tk.Label(
            geo_card,
            text="STATUS: NO TARGET LOADED\nCoordinates, altitude, and precision fixes will show here.",
            fg=TEXT_MUTED, bg=BG_CARD, font=(FONT_MONO, 8), justify="left", anchor="w"
        )
        self.geo_text.pack(fill="x", padx=14, pady=(0, 10))

        # Forensic Metadata Table
        data_card = tk.Frame(left_col, bg=BG_CARD, highlightthickness=1, highlightbackground=BORDER)
        data_card.pack(fill="both", expand=True)

        tk.Label(data_card, text="EXIF FORENSIC METADATA ATTRIBUTES", fg=ACCENT_CYAN, bg=BG_CARD, font=(FONT_MAIN, 9, "bold")).pack(anchor="w", padx=14, pady=(8, 4))

        scroll_wrap = tk.Frame(data_card, bg=BG_CARD)
        scroll_wrap.pack(fill="both", expand=True, padx=10, pady=(0, 8))

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

        # RIGHT COLUMN (Visual Inspection Preview + Large In-App Live Map)
        right_col = tk.Frame(body, bg=BG)
        right_col.grid(row=0, column=1, sticky="nsew")

        # Top Right: Visual Preview of Image
        img_card = tk.Frame(right_col, bg=BG_CARD, highlightthickness=1, highlightbackground=BORDER)
        img_card.pack(fill="x", pady=(0, 8))

        tk.Label(img_card, text="IMAGE VISUAL INSPECTION", fg=ACCENT_CYAN, bg=BG_CARD, font=(FONT_MAIN, 8, "bold")).pack(anchor="w", padx=12, pady=(6, 2))
        self.canvas_preview = tk.Canvas(img_card, bg=INPUT_BG, height=180, highlightthickness=0)
        self.canvas_preview.pack(fill="x", padx=10, pady=(0, 4))
        self.img_caption = tk.Label(img_card, text="No target image loaded", fg=TEXT_MUTED, bg=BG_CARD, font=(FONT_MAIN, 7))
        self.img_caption.pack(pady=(0, 6))
        self.draw_placeholder()

        # Bottom Right: Embedded Interactive Satellite/Street Map
        map_card = tk.Frame(right_col, bg=BG_CARD, highlightthickness=1, highlightbackground=BORDER)
        map_card.pack(fill="both", expand=True)

        map_header = tk.Frame(map_card, bg=BG_CARD)
        map_header.pack(fill="x", padx=12, pady=(8, 4))
        tk.Label(map_header, text="🗺  LIVE EMBEDDED GEOLOCATION RADAR", fg=ACCENT_CYAN, bg=BG_CARD, font=(FONT_MAIN, 9, "bold")).pack(side="left")

        # In-App Map Widget
        self.map_container = tk.Frame(map_card, bg=INPUT_BG)
        self.map_container.pack(fill="both", expand=True, padx=10, pady=(0, 10))

        if MAP_AVAILABLE:
            self.map_view = tkintermapview.TkinterMapView(self.map_container, corner_radius=0)
            self.map_view.pack(fill="both", expand=True)
            # Default center on India
            self.map_view.set_position(20.5937, 78.9629)
            self.map_view.set_zoom(4)
            self.map_marker = None
        else:
            tk.Label(
                self.map_container,
                text="Map module missing. Install via:\npip install tkintermapview",
                fg=ACCENT_WARN, bg=INPUT_BG, font=(FONT_MONO, 9)
            ).pack(expand=True)

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
            tk.Label(row, text=f, fg=TEXT_MUTED, bg=BG_CARD, font=(FONT_MAIN, 7, "bold"), width=20, anchor="w").pack(side="left", padx=8)
            lbl = tk.Label(row, text="--", fg=TEXT_WHITE, bg=INPUT_BG, font=(FONT_MONO, 8), anchor="w", padx=8, pady=4, wraplength=380, justify="left")
            lbl.pack(side="left", fill="x", expand=True)
            self.row_labels[f] = lbl

    def draw_placeholder(self):
        self.canvas_preview.delete("all")
        w = max(self.canvas_preview.winfo_width(), 260)
        h = max(self.canvas_preview.winfo_height(), 180)
        self.canvas_preview.create_rectangle(10, 10, w - 10, h - 10, outline=BORDER, width=1)
        self.canvas_preview.create_text(w // 2, h // 2, text="[ IMAGE PREVIEW ]", fill=TEXT_MUTED, font=(FONT_MAIN, 8))

    # --- FILE DROPS & BROWSING ---
    def browse_file(self):
        path = filedialog.askopenfilename(
            title="Select Image File",
            filetypes=[("Image Files", "*.jpg *.jpeg *.png *.tiff *.webp"), ("All Files", "*.*")]
        )
        if path:
            self.process_image(path)

    def on_file_drop(self, event):
        path = event.data.strip()
        # Clean paths for Linux URI format (file://) and Windows braces ({})
        if path.startswith("{") and path.endswith("}"):
            path = path[1:-1]
        if path.startswith("file://"):
            path = path[7:]
        path = os.path.abspath(path)

        if os.path.isfile(path):
            self.process_image(path)

    def process_image(self, path):
        self.current_image_path = path
        filename = os.path.basename(path)
        self.drop_label.config(text=f"LOADED FILE:\n{filename}")
        self.status_lbl.config(text="● ANALYZING", fg=ACCENT_WARN)

        self.render_image_preview(path)
        threading.Thread(target=self._metadata_worker, args=(path,), daemon=True).start()

    def render_image_preview(self, path):
        try:
            with Image.open(path) as img:
                img = img.convert("RGB")
                w = max(self.canvas_preview.winfo_width(), 240)
                h = max(self.canvas_preview.winfo_height(), 160)
                img.thumbnail((w - 20, h - 20), Image.Resampling.LANCZOS)
                self.preview_image = ImageTk.PhotoImage(img)

            self.canvas_preview.delete("all")
            self.canvas_preview.create_image(w // 2, h // 2, image=self.preview_image, anchor="center")
            self.img_caption.config(text=os.path.basename(path)[:36], fg=ACCENT_CYAN)
        except Exception:
            self.draw_placeholder()

    # --- ADVANCED METADATA & DEEP GPS PARSER ---
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
        except Exception:
            pass

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
            except Exception:
                pass

        self.root.after(0, lambda: self.render_results(metadata, gps_info, lat, lon))

    def render_results(self, meta, gps_raw, lat, lon):
        self.status_lbl.config(text="● ANALYSIS COMPLETE", fg=ACCENT_GREEN)
        self.extracted_data = meta
        self.extracted_gps = (lat, lon) if (lat and lon) else None

        def get_val(*keys):
            for k in keys:
                for mk, v in meta.items():
                    if k.lower() == mk.lower() and v:
                        return str(v).strip()
            return "N/A"

        # Populate Attributes
        self.row_labels["CAMERA MAKE"].config(text=get_val("Make"))
        self.row_labels["CAMERA MODEL"].config(text=get_val("Model"))
        self.row_labels["DATE & TIME TAKEN"].config(text=get_val("DateTimeOriginal", "DateTime"))
        self.row_labels["SHUTTER SPEED"].config(text=get_val("ExposureTime", "ShutterSpeedValue"))
        self.row_labels["APERTURE (F-NUMBER)"].config(text=get_val("FNumber", "ApertureValue"))
        self.row_labels["ISO SPEED"].config(text=get_val("ISOSpeedRatings", "ISO"))
        self.row_labels["FOCAL LENGTH"].config(text=get_val("FocalLength"))
        self.row_labels["IMAGE RESOLUTION"].config(text=meta.get("IMAGE RESOLUTION", "N/A"))
        self.row_labels["SOFTWARE / OS"].config(text=get_val("Software"))

        # In-App Live Map Update
        if lat and lon:
            self.row_labels["GPS LATITUDE"].config(text=f"{lat:.6f}")
            self.row_labels["GPS LONGITUDE"].config(text=f"{lon:.6f}")
            self.row_labels["ALTITUDE"].config(text=f"{gps_raw.get('GPSAltitude', 'N/A')} m")

            self.geo_text.config(
                text=f"STATUS    : 🎯 GEOLOCATION LOCKED\nLATITUDE  : {lat:.6f}\nLONGITUDE : {lon:.6f}\nRADAR     : Live Map Auto-Centered on Target Location",
                fg=ACCENT_GREEN
            )

            # Move In-App Map Directly to Coordinates
            if MAP_AVAILABLE and hasattr(self, "map_view"):
                self.map_view.set_position(lat, lon)
                self.map_view.set_zoom(17)

                if self.map_marker:
                    self.map_view.delete(self.map_marker)
                self.map_marker = self.map_view.set_marker(lat, lon, text=f"Target: {lat:.4f}, {lon:.4f}")
        else:
            self.row_labels["GPS LATITUDE"].config(text="NO GPS TAG")
            self.row_labels["GPS LONGITUDE"].config(text="NO GPS TAG")
            self.row_labels["ALTITUDE"].config(text="N/A")

            self.geo_text.config(
                text="GPS STATUS: NO COORDINATES IN METADATA\n"
                     "Reason: Phone camera had 'Location/Geotagging' turned OFF when photo was taken,\n"
                     "or photo was shared through chat apps without Document mode.",
                fg=ACCENT_WARN
            )

    def copy_metadata(self):
        if not self.extracted_data:
            return
        lines = [f"{k}: {v}" for k, v in self.extracted_data.items()]
        if self.extracted_gps:
            lines.append(f"GPS_COORDINATES: {self.extracted_gps[0]}, {self.extracted_gps[1]}")
        self.root.clipboard_clear()
        self.root.clipboard_append("\n".join(lines))
        messagebox.showinfo("Copied", "All EXIF metadata copied to clipboard!")


def main():
    root = TkRoot()
    app = PhotoReconApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
