.p from PIL import Image, ImageOps
from ui.bulletin import BulletinHelper
import os
import json

iipath = "/storage/emulated/0/Pictures/FyS9F7PaMAELQy-.jpg"
size = 25
dirpath = "/storage/emulated/0/s/ChatExport_2026-02-25/photos"
cache_path = os.path.join(dirpath, "brightness_cache.json")

#================ВИДЖЕТ
#===============
#===============
#===============
#===============
#===============
#===============
#===============
#===============
#===============
#===============
from android.content import Context, Intent
from android.view import WindowManager, ViewGroup, Gravity, View
from android.widget import TextView, Button 
from android.graphics import PixelFormat, Color
from android.provider import Settings
from android.os import Build
from android.app import Application
from client_utils import get_last_fragment, run_on_ui_thread
from org.telegram.messenger import AndroidUtilities  # Для dp в px и т.д.

overlay_view = None

def create_overlay():
    global overlay_view
    if not check_overlay_permission():
        request_overlay_permission()
        return

    context = application
    wm = context.getSystemService(Context.WINDOW_SERVICE)

    text_view = TextView(context)
    text_view.setText("надпись")
    text_view.setTextColor(Color.WHITE)
    text_view.setBackgroundColor(Color.argb(128, 0, 0, 0))
    text_view.setPadding(20, 10, 20, 10) 

    params = WindowManager.LayoutParams(
        ViewGroup.LayoutParams.WRAP_CONTENT,
        ViewGroup.LayoutParams.WRAP_CONTENT,
        WindowManager.LayoutParams.TYPE_APPLICATION_OVERLAY if Build.VERSION.SDK_INT >= Build.VERSION_CODES.O else WindowManager.LayoutParams.TYPE_PHONE,
        WindowManager.LayoutParams.FLAG_NOT_FOCUSABLE | WindowManager.LayoutParams.FLAG_NOT_TOUCH_MODAL | WindowManager.LayoutParams.FLAG_WATCH_OUTSIDE_TOUCH,
        PixelFormat.TRANSLUCENT
    )
    params.gravity = Gravity.TOP | Gravity.CENTER_HORIZONTAL
    params.x = 0
    params.y = AndroidUtilities.dp(50)

    wm.addView(text_view, params)
    overlay_view = text_view

def remove_overlay():
    global overlay_view
    if overlay_view:
        context = application
        wm = context.getSystemService(Context.WINDOW_SERVICE)
        wm.removeView(overlay_view)
        overlay_view = None

def check_overlay_permission():
    if Build.VERSION.SDK_INT >= Build.VERSION_CODES.M:
        return Settings.canDrawOverlays(application)
    return True

def request_overlay_permission():
    context = get_last_fragment().getContext()
    intent = Intent(Settings.ACTION_MANAGE_OVERLAY_PERMISSION)
    context.startActivity(intent)

#ИЗОБРАЖЕНИЕ
run_on_ui_thread(create_overlay)
def log(info):
    run_on_ui_thread(lambda: overlay_view.setText(str(info))) 
    #BulletinHelper.show_success(str(info))

def get_image_files():
    return sorted(
        f for f in os.listdir(dirpath)
        if f.lower().endswith(('.jpg', '.jpeg', '.png'))
    )

def create_brightness_cache():
    image_files = get_image_files()
    brightness_data = []
    
    for i, filename in enumerate(image_files):
        if i % 10 == 0 and i > 0:
            log(f"Обработано {i} / {len(image_files)} изображений")
            
        fullpath = os.path.join(dirpath, filename)
        try:
            with Image.open(fullpath) as img:
                img = img.resize((64, 64), Image.Resampling.LANCZOS)
                if img.mode != 'RGB':
                    img = img.convert('RGB')

                pixels = list(img.getdata())
                if not pixels:
                    avg = 0
                else:
                    avg = sum(sum(p) / 3 for p in pixels) / len(pixels)
                
                brightness_data.append({
                    'filename': filename,
                    'brightness': avg
                })
        except Exception as e:
            log(f"Ошибка при обработке {filename}: {e}")
            continue
    
    with open(cache_path, 'w', encoding='utf-8') as f:
        json.dump(brightness_data, f, indent=2)
    
    log(f"Кэш яркостей создан: {len(brightness_data)} записей")
    return brightness_data

def load_or_create_brightness_map():
    image_files = get_image_files()
    
    if not image_files:
        raise FileNotFoundError("В папке нет изображений")
    
    try:
        with open(cache_path, 'r', encoding='utf-8') as f:
            cached = json.load(f)
        
        cached_files = [item['filename'] for item in cached]
        if cached_files == image_files:
            log(f"Используется кэш яркостей ({len(cached)} записей)")
            return cached
        else:
            log("Пересоздается кэш яркостей")
    except Exception as e:
        log(f"Кэш не удалось прочитать ({e}) - создается новый")
    
    return create_brightness_cache()

brightness_data = load_or_create_brightness_map()

brightness_values = [item['brightness'] for item in brightness_data]
if not brightness_values:
    raise ValueError("Не удалось получить ни одной яркости")

min_b = min(brightness_values)
max_b = max(brightness_values)
range_b = max_b - min_b if max_b > min_b else 1

normalized = [
    (val - min_b) / range_b * 255
    for val in brightness_values
]


norm_list = normalized

ii = Image.open(iipath).convert('RGB')
w, h = ii.size
canvas = Image.new("RGB", (w, h), (0, 0, 0))

num_w = w // size
num_h = h // size

log(f"{num_w} × {num_h} тайлов")

for y in range(num_h):
    for x in range(num_w):
        left   = x * size
        upper  = y * size
        right  = left + size
        lower  = upper + size
        
        block = ii.crop((left, upper, right, lower))
        
        avg_img = block.resize((1, 1), Image.Resampling.LANCZOS)
        r, g, b = avg_img.getpixel((0, 0))
        target = (r + g + b) / 3.0
        
        diffs = [abs(n - target) for n in norm_list]
        idx = diffs.index(min(diffs))
        
        filename = brightness_data[idx]['filename']
        fullpath = os.path.join(dirpath, filename)
        
        try:
            tile = Image.open(fullpath).convert('RGB')
            tile = tile.resize((size, size), Image.Resampling.LANCZOS)
            canvas.paste(tile, (left, upper))
        except Exception as e:
            log(f"Не удалось загрузить тайл {filename}: {e}")
            pass

        if (y * num_w + x + 1) % 50 == 0:
            log(f"Вставленно {y * num_w + x + 1} / {num_w * num_h} тайлов")
            
run_on_ui_thread(remove_overlay)
print_photo(canvas)