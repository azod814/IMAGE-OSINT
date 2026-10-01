"""
IMAGE EXIF & GPS RECON TOOL (AZOD814) - v3.0 Deep OSINT
High-Precision Satellite Forensics & Complete Raw Metadata Inspector
"""

import os
import sys
import json
import threading
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from PIL import Image, ImageTk
from PIL.ExifTags import TAGS, GPSTAGS, IFD

# Satellite & Map View Support
try:
    import tkintermapview
    MAP_AVAILABLE = True
except ImportError:
    MAP_AVAILABLE = False

# Native Drag and Drop
DND_AVAILABLE = False
try:
    from tkinterdnd2 import DND_FILES, TkinterDnD
    TkRoot = TkinterDnD.Tk
    DND_AVAILABLE = True
except ImportError:
    TkRoot = tk.Tk

# Secondary Deep Parser
try:
    import exifread
    EXIFREAD_AVAILABLE = True
except ImportError:
    EXIFREAD_AVAILABLE = False


# Cyber Tactical UI Colors
BG_DARK = "#090d13"
BG_CARD = "#111823"
BG_CELL = "#15202d"
BORDER = "#1f2e42"
ACCENT_CYAN = "#00e5ff"
ACCENT_GREEN = "#10b981"
ACCENT_AMBER = "#f59e0b"
ACCENT_RED = "#ef4444"
TEXT_MAIN = "#f1f5f9"
TEXT_DIM = "#94a3b8"

FONT_MAIN = "Segoe UI" if os.name == "nt" else "DejaVu Sans"
FONT_MONO = "Consolas" if os.name == "nt" else "DejaVu Sans Mono"


def parse_rational(val):
    """Safely converts IFDRational, tuples, or floats to pure float."""
    try:
        if hasattr(val, "real") and hasattr(val, "imag"):
            return float(val)
        if hasattr(val, "numerator") and hasattr(val, "denominator"):
            return float(val.numerator) / float(val.denominator) if val.denominator != 0 else float(val.numerator)
        if isinstance(val, (tuple, list)):
            return [parse_rational(x) for x in val]
        return float(val)
    except Exception:
        return val


def dms_to_decimal(coords, ref):
    """Converts Degrees, Minutes, Seconds to Decimal Latitude/Longitude."""
    try:
        deg = parse_rational(coords[0])
        minute = parse_rational(coords[1])
        sec = parse_rational(coords[2])
        dec = float(deg) + (float(minute) / 60.0) + (float(sec) / 3600.0)
        if ref in ["S", "W"]:
            dec = -dec
        return dec
    except Exception:
        return None


class DeepPhotoOSINTApp:
    def __init__(self, root):
        self.root = root
        self.root.title("ADVANCED EXIF & GEOLOCATION SATELLITE RECON // v3.0")
        self.root.geometry("1540x940")
        self.root.minsize(1100, 720)
        self.root.configure(bg=BG_DARK)

        self.current_image_path = None
        self.metadata_records = []
        self.gps_coords = None
        self.preview_image = None
        self.map_marker = None

        self.setup_styles()
        self.build_ui()

    def setup_styles(self):
        style = ttk.Style()
        style.theme_use("clam")
        style.configure(
            "Treeview",
            background=BG_CELL,
            foreground=TEXT_MAIN,
            fieldbackground=BG_CELL,
            font=(FONT_MONO, 8),
            rowheight=24,
            borderwidth=0
        )
        style.configure(
            "Treeview.Heading",
            background=BG_CARD,
            foreground=ACCENT_CYAN,
            font=(FONT_MAIN, 9, "bold"),
            borderwidth=1,
            relief="flat"
        )
        style.map("Treeview", background=[("selected", "#1e3a5f")], foreground=[("selected", "#ffffff")])

    def build_ui(self):
        # 1. Header Toolbar
        topbar = tk.Frame(self.root, bg=BG_CARD, height=64, highlightthickness=1, highlightbackground=BORDER)
        topbar.pack(fill="x", padx=12, pady=(10, 6))
        topbar.pack_propagate(False)

        title_box = tk.Frame(topbar, bg=BG_CARD)
        title_box.pack(side="left", padx=16)
        tk.Label(title_box, text="⚡ DEEP EXIF & SATELLITE FORENSICS RADAR", fg=ACCENT_CYAN, bg=BG_CARD, font=(FONT_MAIN, 13, "bold")).pack(anchor="w")
        tk.Label(title_box, text="DUAL-PIPELINE PARSING ENGINE (PIL-IFD + EXIFREAD DEEP EXTRACT)", fg=TEXT_DIM, bg=BG_CARD, font=(FONT_MAIN, 8)).pack(anchor="w")

        status_box = tk.Frame(topbar, bg=BG_CARD)
        status_box.pack(side="right", padx=16)
        self.status_main = tk.Label(status_box, text="● ENGINE STANDBY", fg=ACCENT_GREEN, bg=BG_CARD, font=(FONT_MONO, 10, "bold"))
        self.status_main.pack(anchor="e")
        self.status_sub = tk.Label(status_box, text="Ready for raw image data", fg=TEXT_DIM, bg=BG_CARD, font=(FONT_MONO, 8))
        self.status_sub.pack(anchor="e")

        # 2. Main Work Area
        main_box = tk.Frame(self.root, bg=BG_DARK)
        main_box.pack(fill="both", expand=True, padx=12, pady=4)
        main_box.grid_columnconfigure(0, weight=5)
        main_box.grid_columnconfigure(1, weight=6)
        main_box.grid_rowconfigure(0, weight=1)

        # ================= LEFT COLUMN =================
        left_panel = tk.Frame(main_box, bg=BG_DARK)
        left_panel.grid(row=0, column=0, sticky="nsew", padx=(0, 6))

        # Dropzone & Control Bar
        control_card = tk.Frame(left_panel, bg=BG_CARD, highlightthickness=1, highlightbackground=BORDER)
        control_card.pack(fill="x", pady=(0, 6))

        self.drop_box = tk.Frame(control_card, bg="#070a0e", height=90, highlightthickness=1, highlightbackground="#1b2838")
        self.drop_box.pack(fill="x", padx=10, pady=8)
        self.drop_box.pack_propagate(False)

        self.drop_lbl = tk.Label(
            self.drop_box,
            text="DRAG & DROP IMAGE FILE HERE\n(OR CLICK BUTTONS BELOW)",
            fg=TEXT_MAIN, bg="#070a0e", font=(FONT_MONO, 9, "bold"), justify="center"
        )
        self.drop_lbl.pack(expand=True)

        if DND_AVAILABLE:
            for w in (self.drop_box, self.drop_lbl):
                w.drop_target_register(DND_FILES)
                w.dnd_bind("<<Drop>>", self.handle_drop)

        btn_row = tk.Frame(control_card, bg=BG_CARD)
        btn_row.pack(fill="x", padx=10, pady=(0, 8))

        tk.Button(
            btn_row, text="📁 SELECT FILE", command=self.select_file,
            bg="#0284c7", fg="#ffffff", activebackground="#0369a1",
            font=(FONT_MAIN, 8, "bold"), relief="flat", padx=14, pady=6, cursor="hand2"
        ).pack(side="left", fill="x", expand=True, padx=(0, 4))

        tk.Button(
            btn_row, text="📋 COPY ALL DATA", command=self.copy_all,
            bg="#1e293b", fg=TEXT_MAIN, activebackground=BORDER,
            font=(FONT_MAIN, 8, "bold"), relief="flat", padx=14, pady=6, cursor="hand2"
        ).pack(side="left", fill="x", expand=True, padx=4)

        tk.Button(
            btn_row, text="💾 EXPORT JSON", command=self.export_json,
            bg="#1e293b", fg=TEXT_MAIN, activebackground=BORDER,
            font=(FONT_MAIN, 8, "bold"), relief="flat", padx=14, pady=6, cursor="hand2"
        ).pack(side="left", fill="x", expand=True, padx=(4, 0))

        # Geolocation Status Card
        self.geo_card = tk.Frame(left_panel, bg=BG_CARD, highlightthickness=1, highlightbackground=BORDER)
        self.geo_card.pack(fill="x", pady=(0, 6))

        tk.Label(self.geo_card, text="📍 SATELLITE GEOLOCATION FIX", fg=ACCENT_CYAN, bg=BG_CARD, font=(FONT_MAIN, 9, "bold")).pack(anchor="w", padx=12, pady=(6, 2))
        self.geo_details = tk.Label(
            self.geo_card,
            text="STATUS: NO IMAGE LOADED\nLatitude: -- | Longitude: -- | Altitude: --",
            fg=TEXT_DIM, bg=BG_CARD, font=(FONT_MONO, 8), justify="left", anchor="w"
        )
        self.geo_details.pack(fill="x", padx=12, pady=(0, 8))

        # Comprehensive Deep Metadata Tree
        tree_card = tk.Frame(left_panel, bg=BG_CARD, highlightthickness=1, highlightbackground=BORDER)
        tree_card.pack(fill="both", expand=True)

        tree_header = tk.Frame(tree_card, bg=BG_CARD)
        tree_header.pack(fill="x", padx=10, pady=(6, 4))
        tk.Label(tree_header, text="DETAILED METADATA ATTRIBUTES", fg=ACCENT_CYAN, bg=BG_CARD, font=(FONT_MAIN, 9, "bold")).pack(side="left")
        
        self.search_var = tk.StringVar()
        self.search_var.trace("w", self.filter_tree)
        search_entry = tk.Entry(tree_header, textvariable=self.search_var, bg="#070a0e", fg=TEXT_MAIN, insertbackground=ACCENT_CYAN, font=(FONT_MONO, 8), width=18)
        search_entry.pack(side="right")
        tk.Label(tree_header, text="Filter: ", fg=TEXT_DIM, bg=BG_CARD, font=(FONT_MAIN, 8)).pack(side="right")

        tree_box = tk.Frame(tree_card, bg=BG_CARD)
        tree_box.pack(fill="both", expand=True, padx=8, pady=(0, 8))

        self.tree = ttk.Treeview(tree_box, columns=("Category", "Tag", "Value"), show="headings", selectmode="browse")
        self.tree.heading("Category", text="CATEGORY")
        self.tree.heading("Tag", text="METADATA FIELD")
        self.tree.heading("Value", text="VALUE")
        self.tree.column("Category", width=100, minwidth=80)
        self.tree.column("Tag", width=180, minwidth=140)
        self.tree.column("Value", width=260, minwidth=180)

        tree_sbar = ttk.Scrollbar(tree_box, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=tree_sbar.set)
        self.tree.pack(side="left", fill="both", expand=True)
        tree_sbar.pack(side="right", fill="y")

        # ================= RIGHT COLUMN =================
        right_panel = tk.Frame(main_box, bg=BG_DARK)
        right_panel.grid(row=0, column=1, sticky="nsew", padx=(6, 0))

        # Visual Image Inspector
        preview_card = tk.Frame(right_panel, bg=BG_CARD, highlightthickness=1, highlightbackground=BORDER)
        preview_card.pack(fill="x", pady=(0, 6))

        tk.Label(preview_card, text="TARGET IMAGE PREVIEW", fg=ACCENT_CYAN, bg=BG_CARD, font=(FONT_MAIN, 9, "bold")).pack(anchor="w", padx=12, pady=(6, 2))
        self.canvas = tk.Canvas(preview_card, bg="#070a0e", height=180, highlightthickness=0)
        self.canvas.pack(fill="x", padx=10, pady=(0, 4))
        self.preview_lbl = tk.Label(preview_card, text="No target loaded", fg=TEXT_DIM, bg=BG_CARD, font=(FONT_MAIN, 8))
        self.preview_lbl.pack(pady=(0, 6))
        self.render_canvas_placeholder()

        # Satellite Radar Map Card
        map_card = tk.Frame(right_panel, bg=BG_CARD, highlightthickness=1, highlightbackground=BORDER)
        map_card.pack(fill="both", expand=True)

        map_top = tk.Frame(map_card, bg=BG_CARD)
        map_top.pack(fill="x", padx=10, pady=(6, 4))
        tk.Label(map_top, text="🛰 SATELLITE TACTICAL MAP", fg=ACCENT_CYAN, bg=BG_CARD, font=(FONT_MAIN, 9, "bold")).pack(side="left")

        # Map Layer Toggles
        tk.Button(map_top, text="Satellite (Hybrid)", command=self.set_satellite_mode, bg="#1e293b", fg=TEXT_MAIN, font=(FONT_MAIN, 7, "bold"), relief="flat", padx=6).pack(side="right", padx=2)
        tk.Button(map_top, text="Street View", command=self.set_street_mode, bg="#1e293b", fg=TEXT_MAIN, font=(FONT_MAIN, 7, "bold"), relief="flat", padx=6).pack(side="right", padx=2)

        self.map_holder = tk.Frame(map_card, bg="#070a0e")
        self.map_holder.pack(fill="both", expand=True, padx=8, pady=(0, 8))

        if MAP_AVAILABLE:
            self.map_view = tkintermapview.TkinterMapView(self.map_holder, corner_radius=0)
            self.map_view.pack(fill="both", expand=True)
            self.set_satellite_mode()
            self.map_view.set_position(28.6139, 77.2090)  # Default center
            self.map_view.set_zoom(5)
        else:
            tk.Label(self.map_holder, text="Map library missing.\nRun: pip install tkintermapview", fg=ACCENT_AMBER, bg="#070a0e", font=(FONT_MONO, 10)).pack(expand=True)

    def set_satellite_mode(self):
        if MAP_AVAILABLE and hasattr(self, "map_view"):
            # High-Resolution Google Satellite Hybrid View
            self.map_view.set_tile_server(
                "https://mt0.google.com/vt/lyrs=y&hl=en&x={x}&y={y}&z={z}&s=Ga",
                max_zoom=20
            )

    def set_street_mode(self):
        if MAP_AVAILABLE and hasattr(self, "map_view"):
            self.map_view.set_tile_server("https://a.tile.openstreetmap.org/{z}/{x}/{y}.png", max_zoom=19)

    def render_canvas_placeholder(self):
        self.canvas.delete("all")
        w = max(self.canvas.winfo_width(), 300)
        h = max(self.canvas.winfo_height(), 180)
        self.canvas.create_rectangle(8, 8, w - 8, h - 8, outline=BORDER, width=1)
        self.canvas.create_text(w // 2, h // 2, text="[ IMAGE FEED OFFLINE ]", fill=TEXT_DIM, font=(FONT_MONO, 8))

    def handle_drop(self, event):
        path = event.data.strip()
        if path.startswith("{") and path.endswith("}"):
            path = path[1:-1]
        if path.startswith("file://"):
            path = path[7:]
        path = os.path.abspath(path)
        if os.path.isfile(path):
            self.start_processing(path)

    def select_file(self):
        path = filedialog.askopenfilename(
            title="Select Target Image",
            filetypes=[("Image Files", "*.jpg *.jpeg *.png *.heic *.tiff *.webp"), ("All Files", "*.*")]
        )
        if path:
            self.start_processing(path)

    def start_processing(self, path):
        self.current_image_path = path
        self.drop_lbl.config(text=f"LOADED:\n{os.path.basename(path)}")
        self.status_main.config(text="● EXTRACTING", fg=ACCENT_AMBER)
        self.status_sub.config(text="Deep scanning raw EXIF / GPS structures...")

        self.update_image_preview(path)
        threading.Thread(target=self._deep_extractor_worker, args=(path,), daemon=True).start()

    def update_image_preview(self, path):
        try:
            with Image.open(path) as img:
                img = img.convert("RGB")
                w = max(self.canvas.winfo_width(), 260)
                h = max(self.canvas.winfo_height(), 180)
                img.thumbnail((w - 16, h - 16), Image.Resampling.LANCZOS)
                self.preview_image = ImageTk.PhotoImage(img)

            self.canvas.delete("all")
            self.canvas.create_image(w // 2, h // 2, image=self.preview_image, anchor="center")
            self.preview_lbl.config(text=f"{os.path.basename(path)} ({os.path.getsize(path)/1024:.1f} KB)", fg=ACCENT_CYAN)
        except Exception:
            self.render_canvas_placeholder()

    # --- DUAL-ENGINE EXTRACTION LOGIC ---
    def _deep_extractor_worker(self, path):
        records = []
        gps_lat = None
        gps_lon = None
        altitude = None

        # 1. Base Image Properties
        try:
            with Image.open(path) as im:
                records.append(("Basic", "File Path", path))
                records.append(("Basic", "File Size", f"{os.path.getsize(path)/1024:.2f} KB"))
                records.append(("Basic", "Format", str(im.format)))
                records.append(("Basic", "Dimensions", f"{im.width} x {im.height}"))
                records.append(("Basic", "Color Mode", str(im.mode)))

                # 2. Modern Pillow IFD Parsing
                exif = im.getexif()
                if exif:
                    # Root Tags
                    for tag_id, val in exif.items():
                        name = TAGS.get(tag_id, f"Tag_{tag_id}")
                        if name != "GPSInfo":
                            records.append(("EXIF", name, str(val)))

                    # Extended Exif IFD
                    try:
                        exif_ifd = exif.get_ifd(IFD.Exif)
                        for tag_id, val in exif_ifd.items():
                            name = TAGS.get(tag_id, f"SubTag_{tag_id}")
                            records.append(("ExifIFD", name, str(val)))
                    except Exception:
                        pass

                    # Direct GPS IFD
                    try:
                        gps_ifd = exif.get_ifd(IFD.GPSInfo)
                        for gid, gval in gps_ifd.items():
                            gname = GPSTAGS.get(gid, f"GPS_{gid}")
                            records.append(("GPS_Raw", gname, str(gval)))

                        lat_raw = gps_ifd.get(2)   # GPSLatitude
                        lat_ref = gps_ifd.get(1)   # GPSLatitudeRef
                        lon_raw = gps_ifd.get(4)   # GPSLongitude
                        lon_ref = gps_ifd.get(3)   # GPSLongitudeRef
                        alt_raw = gps_ifd.get(6)   # GPSAltitude

                        if lat_raw and lon_raw:
                            gps_lat = dms_to_decimal(lat_raw, lat_ref)
                            gps_lon = dms_to_decimal(lon_raw, lon_ref)
                        if alt_raw:
                            altitude = f"{parse_rational(alt_raw):.2f} m"
                    except Exception:
                        pass
        except Exception as e:
            records.append(("Error", "Pillow Extraction", str(e)))

        # 3. ExifRead Secondary Deep Scan (Fallback & Enrichment)
        if EXIFREAD_AVAILABLE:
            try:
                with open(path, "rb") as f:
                    tags = exifread.process_file(f, details=True)
                    for t, val in tags.items():
                        if not any(r[1] == t for r in records):
                            records.append(("DeepRaw", t, str(val)))

                    # If GPS was not recovered by Pillow, try ExifRead
                    if gps_lat is None and "GPS GPSLatitude" in tags and "GPS GPSLongitude" in tags:
                        try:
                            def to_dec(ratio_list, ref):
                                parts = [float(x.num) / float(x.den) for x in ratio_list.values]
                                res = parts[0] + parts[1]/60.0 + parts[2]/3600.0
                                if ref in ["S", "W"]:
                                    res = -res
                                return res

                            lat_ref = str(tags.get("GPS GPSLatitudeRef", "N"))
                            lon_ref = str(tags.get("GPS GPSLongitudeRef", "E"))
                            gps_lat = to_dec(tags["GPS GPSLatitude"], lat_ref)
                            gps_lon = to_dec(tags["GPS GPSLongitude"], lon_ref)
                            if "GPS GPSAltitude" in tags:
                                alt_v = tags["GPS GPSAltitude"].values[0]
                                altitude = f"{float(alt_v.num)/float(alt_v.den):.2f} m"
                        except Exception:
                            pass
            except Exception as e:
                records.append(("Error", "ExifRead", str(e)))

        self.root.after(0, lambda: self.render_final_data(records, gps_lat, gps_lon, altitude))

    def render_final_data(self, records, lat, lon, altitude):
        self.metadata_records = records
        self.gps_coords = (lat, lon) if (lat is not None and lon is not None) else None

        # Populate Table
        self.populate_tree(records)

        # Update Status & GPS Panel
        if self.gps_coords:
            self.status_main.config(text="● GEOLOCATION LOCKED", fg=ACCENT_GREEN)
            self.status_sub.config(text=f"Total Attributes: {len(records)} | Precision Coordinates Verified")

            self.geo_details.config(
                text=f"STATUS    : 🎯 COORDINATES ACQUIRED\n"
                     f"Latitude  : {lat:.7f}\n"
                     f"Longitude : {lon:.7f}\n"
                     f"Altitude  : {altitude or 'Not Recorded'}\n"
                     f"Google URL: https://www.google.com/maps?q={lat},{lon}",
                fg=ACCENT_GREEN
            )

            # Move and Pin Radar Satellite Map
            if MAP_AVAILABLE and hasattr(self, "map_view"):
                self.map_view.set_position(lat, lon)
                self.map_view.set_zoom(18)
                if self.map_marker:
                    self.map_view.delete(self.map_marker)
                self.map_marker = self.map_view.set_marker(lat, lon, text=f"Target: {lat:.5f}, {lon:.5f}")
        else:
            self.status_main.config(text="● COMPLETED (NO GPS)", fg=ACCENT_AMBER)
            self.status_sub.config(text=f"Total Attributes: {len(records)} | No GPS fix found in metadata block")

            self.geo_details.config(
                text="STATUS: NO GPS EMBEDDED IN IMAGE\n"
                     "Tip 1: Phone settings me Camera app ka 'Location tags' toggle check karo.\n"
                     "Tip 2: WhatsApp document me bhejne par metadata rehta hai, lekin agar photo\n"
                     "kisi editor se pass hui ho ya screenshot ho to GPS clean ho jata hai.",
                fg=ACCENT_AMBER
            )

    def populate_tree(self, records):
        self.tree.delete(*self.tree.get_children())
        for cat, tag, val in records:
            # Highlight GPS and Camera tags
            item = self.tree.insert("", "end", values=(cat, tag, val))
            if "GPS" in cat or "GPS" in tag:
                self.tree.item(item, tags=("gps_tag",))
            elif "Make" in tag or "Model" in tag:
                self.tree.item(item, tags=("cam_tag",))

        self.tree.tag_configure("gps_tag", foreground=ACCENT_GREEN)
        self.tree.tag_configure("cam_tag", foreground=ACCENT_CYAN)

    def filter_tree(self, *args):
        query = self.search_var.get().lower()
        self.tree.delete(*self.tree.get_children())
        for cat, tag, val in self.metadata_records:
            if query in cat.lower() or query in tag.lower() or query in str(val).lower():
                self.tree.insert("", "end", values=(cat, tag, val))

    def copy_all(self):
        if not self.metadata_records:
            return
        lines = [f"[{cat}] {tag} = {val}" for cat, tag, val in self.metadata_records]
        if self.gps_coords:
            lines.append(f"[COORDINATES] {self.gps_coords[0]}, {self.gps_coords[1]}")
            lines.append(f"[GOOGLE_MAPS] https://www.google.com/maps?q={self.gps_coords[0]},{self.gps_coords[1]}")
        self.root.clipboard_clear()
        self.root.clipboard_append("\n".join(lines))
        messagebox.showinfo("Copied", f"Copied {len(lines)} metadata attributes to clipboard!")

    def export_json(self):
        if not self.metadata_records:
            return
        save_path = filedialog.asksaveasfilename(
            defaultextension=".json",
            filetypes=[("JSON File", "*.json")],
            initialfile=f"forensic_report_{int(os.path.getmtime(self.current_image_path)) if self.current_image_path else 'export'}.json"
        )
        if save_path:
            dump_data = {
                "file": self.current_image_path,
                "coordinates": self.gps_coords,
                "attributes": {f"{cat}::{tag}": val for cat, tag, val in self.metadata_records}
            }
            with open(save_path, "w", encoding="utf-8") as f:
                json.dump(dump_data, f, indent=4)
            messagebox.showinfo("Exported", f"Forensic data saved to:\n{save_path}")


def main():
    root = TkRoot()
    app = DeepPhotoOSINTApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
