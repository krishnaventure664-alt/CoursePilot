import sys, io
sys.stdout.reconfigure(encoding='utf-8')
sys.path.insert(0, 'backend')
from services.bge_m3_vector_store_service import collection

results = collection.get(where={'video_id': 'SeBChkBytKE'}, include=['documents', 'metadatas'])
docs = results.get('documents', [])
metas = results.get('metadatas', [])

chunks = []
for doc, meta in zip(docs, metas):
    start = meta.get("start", 0.0) if meta else 0.0
    end = meta.get("end", start + 60.0) if meta else start + 60.0
    chunks.append((start, end, doc))
chunks.sort(key=lambda x: x[0])

total_dur = chunks[-1][1] - chunks[0][0]
print(f"Total duration: {total_dur/60:.1f} minutes ({total_dur/3600:.2f} hours)")

# Dynamic section duration formula:
if total_dur <= 1800.0:        # <= 30 mins
    sec_dur = 900.0             # 15 min blocks
elif total_dur <= 5400.0:      # <= 1.5 hours
    sec_dur = 1500.0            # 25 min blocks
elif total_dur <= 14400.0:     # <= 4 hours
    sec_dur = 2400.0            # 40 min blocks
elif total_dur <= 28800.0:     # <= 8 hours
    sec_dur = 3600.0            # 60 min blocks
else:                          # > 8 hours (e.g. 13-hour Papa videos)
    sec_dur = 4800.0            # 80 min blocks

sections = []
current_section = []
section_start = chunks[0][0]

for start, end, text in chunks:
    if (end - section_start) > sec_dur and current_section:
        sections.append(current_section)
        current_section = [(start, end, text)]
        section_start = start
    else:
        current_section.append((start, end, text))
if current_section:
    sections.append(current_section)

print(f"Dynamically generated {len(sections)} sections of ~{sec_dur/60:.0f} mins each:")
for idx, s in enumerate(sections, 1):
    s_time = int(s[0][0])
    e_time = int(s[-1][1])
    s_label = f"{s_time // 3600:02d}:{(s_time % 3600) // 60:02d}:{s_time % 60:02d}"
    e_label = f"{e_time // 3600:02d}:{(e_time % 3600) // 60:02d}:{e_time % 60:02d}"
    s_words = sum(len(c[2].split()) for c in s)
    print(f"  Section {idx:02d}: {s_label} to {e_label} ({s_words} words)")
