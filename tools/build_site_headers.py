"""Update the three online pages from the shared header component."""
from pathlib import Path
import re
from site_header import site_header

WEB=Path(__file__).resolve().parents[1]/'greenproof/web'
for relative,current in [('index.html','mangrove'),('emissions/index.html','emissions'),('nepal/index.html','nepal')]:
    path=WEB/relative
    html=path.read_text(encoding='utf-8')
    html,count=re.subn(r'<header\b[^>]*>.*?</header>',site_header(current),html,count=1,flags=re.S)
    assert count==1,path
    html=re.sub(r'<link rel="stylesheet" href="(?:/|\.\./)site-header\.css[^\"]*">\s*','',html)
    html=html.replace('</head>','<link rel="stylesheet" href="/site-header.css?v=1">\n</head>',1)
    path.write_text(html,encoding='utf-8')
    print('Updated common header:',relative)
