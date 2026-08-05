#!/usr/bin/env python3
"""
Genera XMLTV con fechas siempre actualizadas ("hoy" + N dias) a partir de
plantillas semanales fijas. Disenado para correr dentro de GitHub Actions
cada dia, asi las fechas nunca quedan viejas.

Cada canal es un archivo de plantilla en epg_manual_templates/*.txt con este formato:

    id=Opa.cr
    nombre=Opa Canal 36
    logo=
    offset=-0600
    dias=7

    Lunes,00:00,Sin informacion
    Lunes,14:00,Central Ahora
    Lunes,16:00,Central Mundo
    Martes,00:00,Sin informacion
    ...

El script genera un archivo <id>.xml por cada plantilla, con las fechas
calculadas en tiempo real al momento de correr (no fechas fijas).
"""
import os
import glob
from datetime import datetime, timedelta

DIAS = ['Lunes','Martes','Miercoles','Jueves','Viernes','Sabado','Domingo']

def esc(s):
    return (s or '').replace('&','&amp;').replace('<','&lt;').replace('>','&gt;').replace('"','&quot;')

def parse_template(path):
    meta = {}
    schedule = {d: [] for d in DIAS}
    with open(path, encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith('#'):
                continue
            if '=' in line and ',' not in line:
                k, v = line.split('=', 1)
                meta[k.strip()] = v.strip()
            elif ',' in line:
                parts = [p.strip() for p in line.split(',', 2)]
                if len(parts) == 3:
                    dia, hora, titulo = parts
                    dia_norm = dia.capitalize().replace('é','e').replace('á','a')
                    if dia_norm in schedule:
                        schedule[dia_norm].append((hora, titulo))
    for d in schedule:
        schedule[d].sort(key=lambda x: x[0])
    return meta, schedule

def generar_xml(meta, schedule):
    ch_id = meta.get('id', 'canal')
    ch_name = meta.get('nombre', ch_id)
    ch_logo = meta.get('logo', '')
    offset = meta.get('offset', '-0600')
    dias_n = int(meta.get('dias', '7'))

    hoy = datetime.now()
    bloques = []
    for i in range(dias_n):
        fecha = hoy + timedelta(days=i)
        dow = DIAS[fecha.weekday()]
        bloques.append((fecha, schedule.get(dow, [])))

    xml = ['<?xml version="1.0" encoding="UTF-8"?>',
           '<tv generator-info-name="generador-epg-manual-auto">',
           f'  <channel id="{esc(ch_id)}">',
           f'    <display-name>{esc(ch_name)}</display-name>']
    if ch_logo:
        xml.append(f'    <icon src="{esc(ch_logo)}" />')
    xml.append('  </channel>')

    for i, (fecha, programas) in enumerate(bloques):
        for j, (hora, titulo) in enumerate(programas):
            h, mi = map(int, hora.split(':'))
            start = fecha.replace(hour=h, minute=mi, second=0)
            if j < len(programas) - 1:
                h2, mi2 = map(int, programas[j+1][0].split(':'))
                stop = fecha.replace(hour=h2, minute=mi2, second=0)
            elif i < len(bloques) - 1 and bloques[i+1][1]:
                nfecha, nprogramas = bloques[i+1]
                h2, mi2 = map(int, nprogramas[0][0].split(':'))
                stop = nfecha.replace(hour=h2, minute=mi2, second=0)
            else:
                stop = start + timedelta(hours=1)
            if stop <= start:
                stop = start + timedelta(hours=1)
            xml.append(f'  <programme start="{start.strftime("%Y%m%d%H%M%S")} {offset}" '
                       f'stop="{stop.strftime("%Y%m%d%H%M%S")} {offset}" channel="{esc(ch_id)}">')
            xml.append(f'    <title>{esc(titulo)}</title>')
            xml.append('  </programme>')

    xml.append('</tv>')
    return '\n'.join(xml)

def main():
    tpl_dir = 'epg_manual_templates'
    if not os.path.isdir(tpl_dir):
        print(f'No existe la carpeta {tpl_dir}, nada que generar.')
        return
    for path in glob.glob(os.path.join(tpl_dir, '*.txt')):
        meta, schedule = parse_template(path)
        xml = generar_xml(meta, schedule)
        out_name = meta.get('id', os.path.basename(path).replace('.txt','')) + '.xml'
        with open(out_name, 'w', encoding='utf-8') as f:
            f.write(xml)
        print(f'Generado: {out_name} ({meta.get("dias","7")} dias)')

if __name__ == '__main__':
    main()
