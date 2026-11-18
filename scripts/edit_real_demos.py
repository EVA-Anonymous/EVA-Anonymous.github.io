"""Reproducible presentation edits; labels are editorial, not planner transcripts."""
import json
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SOURCES = {
    'bottles': '抓水瓶/front.mp4',
    'memory': '三仙归洞/memory_edited_8x_3x_timestamped_silent_fast.mp4',
    'box': '搬箱子/box_8x_timestamped_silent.mp4',
    'chair': '推椅子/chair_8x_timestamped_silent.mp4',
}
# Boundaries refer to supplied edited source seconds, not wall-clock time.
EDITS = {
    'bottles': [(0,18,6,'Pick up a bottle'),(18,48,3,'Pick up a bottle'),
                (48,76,5,'Place the bottle in the box'),(76,110,4,'Pick up the next bottle'),
                (110,152.498,3,'Place the bottle in the box')],
    'memory': [(0,12,4,'Listen to the user instruction'),(12,24,2,'Track the target cup'),
               (24,39,3,'Interrupt - Clear the cluttered table - Pick up the bottle'),
               (39,50,3,'Interrupt - Clear the table - Place the bottle in the box'),
               (50,60,4,'Resume the cup task - Recall the target cup'),
               (60,72,2,'Resume the cup task - Track the target cup'),
               (72,96.72,3,'Press the button for the target cup')],
    'box': [(0,4.8,1.25,'Grasp the box with both hands'),(4.8,6.8,1.1,'Pick up the box'),
            (6.8,11.445,1.15,'Carry the box to the destination')],
    'chair': [(0,2.2,1.15,'Move toward the chair'),(2.2,3.5,1.1,'Grasp the chair backrest'),
              (3.5,6.483,1.1,'Push the chair toward the table')],
}

def source_rates(source, key):
    if key != 'memory':
        return [(0,10000,1 if key=='bottles' else 8)]
    # Read existing 1x / 3x / 8x stamps before cropping them; use their
    # fixed binary glyphs, not assumptions based on the task phase.
    crop='crop=64:48:0:0,format=gray'
    templates={}
    for rate,second in [(1,0),(3,44),(8,20)]:
        raw=subprocess.check_output(['ffmpeg','-v','error','-ss',str(second),'-i',str(source),'-frames:v','1','-vf',crop,'-f','rawvideo','-'])
        templates[rate]=int.from_bytes(bytes(v>180 for v in raw),'big')
    raw=subprocess.check_output(['ffmpeg','-v','error','-i',str(source),'-vf','fps=10,'+crop,'-f','rawvideo','-'])
    frames=[int.from_bytes(bytes(v>180 for v in raw[i:i+3072]),'big') for i in range(0,len(raw),3072)]
    rates=[min(templates,key=lambda k:(f^templates[k]).bit_count()) for f in frames]
    spans=[]
    for i,rate in enumerate(rates):
        if not spans or spans[-1][2]!=rate:spans.append([i/10,(i+1)/10,rate])
        else:spans[-1][1]=(i+1)/10
    return spans

def run(key):
    source=ROOT/'materials/demo-processed'/SOURCES[key]
    segments=[];timeline=[];cursor=0
    for i,(a,b,speed,label) in enumerate(EDITS[key]):
        segments.append(f'[0:v]trim=start={a}:end={b},setpts=(PTS-STARTPTS)/{speed},fps=24,setsar=1[v{i}]')
        end=cursor+(b-a)/speed
        timeline.append({'start':cursor,'end':end,'label':label,'source_start':a,'source_end':b,'relative_speed':speed})
        cursor=end
    segments.append(''.join(f'[v{i}]' for i in range(len(timeline)))+f'concat=n={len(timeline)}:v=1:a=0[cut]')
    # Remove legacy corner timer/speed stamps from already-edited source clips.
    crop='crop=iw:ih-72:0:72,' if key!='bottles' else ''
    filters=crop+'scale=960:540:force_original_aspect_ratio=decrease,pad=960:540:(ow-iw)/2:(oh-ih)/2,setsar=1'
    filters+=',drawbox=x=21:y=483:w=918:h=36:color=0x101c28@0.78:t=fill'
    font='/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf'
    for i,t in enumerate(timeline):
        filters+=f",drawtext=fontfile={font}:text='Subtask - {t['label']}':x=36:y=493:fontsize=16:fontcolor=white:enable='gte(t,{t['start']})*lt(t,{t['end']})'"
    rates=source_rates(source,key)
    for t in timeline:
        for a,b,rate in rates:
            begin=max(a,t['source_start']);end=min(b,t['source_end'])
            if begin>=end:continue
            start=t['start']+(begin-t['source_start'])/t['relative_speed']
            stop=t['start']+(end-t['source_start'])/t['relative_speed']
            speed=rate*t['relative_speed']
            filters+=f",drawtext=fontfile={font}:text='{speed:g}×':x=w-tw-18:y=18:fontsize=14:fontcolor=white:box=1:boxcolor=black@0.35:boxborderw=4:enable='gte(t,{start})*lt(t,{stop})'"
    segments.append('[cut]'+filters+'[out]')
    output=ROOT/'assets/videos'/f'{key}.mp4'
    temporary=output.with_name(key+'.encoding.mp4')
    subprocess.run(['ffmpeg','-v','error','-y','-i',str(source),'-filter_complex',';'.join(segments),
                    '-map','[out]','-an','-c:v','libx264','-preset','slow','-crf','27',
                    '-maxrate','1100k','-bufsize','2200k','-g','48',
                    '-pix_fmt','yuv420p','-movflags','+faststart',str(temporary)],check=True)
    subprocess.run(['ffmpeg','-v','error','-i',str(temporary),'-f','null','-'],check=True)
    temporary.replace(output)
    subprocess.run(['ffmpeg','-v','error','-y','-ss','0.5','-i',str(output),'-frames:v','1',str(ROOT/'assets/images'/f'{key}.jpg')],check=True)
    return {'source':str(source.relative_to(ROOT)),'duration':cursor,'segments':timeline,'source_speed_spans':rates}

if __name__=='__main__':
    data={}
    for key in SOURCES:
        data[key]=run(key)
        print(key,round(data[key]['duration'],2),flush=True)
    (ROOT/'assets/real-demo-edits.json').write_text(json.dumps({'note':'Editorial subtask summaries based on footage, not verbatim agent logs. Relative speeds apply to supplied clips, some already accelerated.','demos':data},indent=2))
