import os

filepath = r'C:\Users\X360\Desktop\KEVWE\HOME\HTML\business.html'

with open(filepath, 'r', encoding='utf-8') as f:
    content = f.read()

fixes = [
    # Shared CSS
    ('href="../../SHARED/CSS/base.css"',       'href="../../SHARED/CSS/base.css"'),
    ('href="../../SHARED/CSS/components.css"', 'href="../../SHARED/CSS/components.css"'),
    ('href="../../SHARED/CSS/animations.css"', 'href="../../SHARED/CSS/animations.css"'),
    ('href="../../SHARED/CSS/utilities.css"',  'href="../../SHARED/CSS/utilities.css"'),

    # Page CSS
    ('href="../CSS/home.css"',      'href="../CSS/home.css"'),
    ('href="../CSS/business.css"',  'href="../CSS/business.css"'),
    ('href="../CSS/bookings.css"',  'href="../CSS/bookings.css"'),
    ('href="../CSS/orders.css"',    'href="../CSS/orders.css"'),
    ('href="../CSS/services.css"',  'href="../CSS/services.css"'),

    # Shared JS
    ('src="../../SHARED/JS/storage.js"', 'src="../../SHARED/JS/storage.js"'),
    ('src="../../SHARED/JS/helpers.js"', 'src="../../SHARED/JS/helpers.js"'),

    # Component JS
    ('src="../JS/components/gallery.js"',         'src="../JS/components/gallery.js"'),
    ('src="../JS/components/business-header.js"', 'src="../JS/components/business-header.js"'),
    ('src="../JS/components/reviews.js"',         'src="../JS/components/reviews.js"'),

    # Renderer JS
    ('src="../JS/renderers/bookings.js"', 'src="../JS/renderers/bookings.js"'),
    ('src="../JS/renderers/orders.js"',   'src="../JS/renderers/orders.js"'),
    ('src="../JS/renderers/services.js"', 'src="../JS/renderers/services.js"'),

    # Main JS
    ('src="../JS/business.js"', 'src="../JS/business.js"'),

    # Internal links
    ('href="index.html"',      'href="index.html"'),
    ('href="industries.html"', 'href="industries.html"'),

    # Auth links
    ('href="../../AUTH/login.html"', 'href="../../AUTH/login.html"'),
]

# Verify paths are correct for HOME/HTML/ location
# ../../SHARED/ = going up HTML/ then HOME/ then reaching KEVWE/SHARED/
# ../CSS/       = going up HTML/ then reaching HOME/CSS/
# ../JS/        = going up HTML/ then reaching HOME/JS/

for old, new in fixes:
    content = content.replace(old, new)

with open(filepath, 'w', encoding='utf-8') as f:
    f.write(content)

print('Fixed business.html')
print('\nPath check:')
print('  HTML file is at: HOME/HTML/business.html')
print('  ../../SHARED/   = KEVWE/SHARED/ ✓')
print('  ../CSS/         = HOME/CSS/ ✓')
print('  ../JS/          = HOME/JS/ ✓')