$(document).ready(() => {
  //Synthesizer
  const synth = new Tone.PolySynth().toDestination();
  synth.volume.value = -12;

  //Rest of it
  const slider = document.getElementById('bpm');
  const output = document.getElementById('bpm_value');
  const test_play = document.getElementById('test_play');

  const text_box = document.getElementById('text');
  const char_cnt = document.getElementById('char_count');
  const base_text = '#lute';
  var text = '';
  var error = '';
  var song = null;
  var reset = null;

  const container = document.getElementById('datatable');

  output.innerHTML = `BPM: ${slider.value}`;
  text_box.innerHTML = `${base_text} ${slider.value} ${text}`;
  char_cnt.innerHTML = `Cheer Message: ${text_box.innerHTML.length} Characters`;

  slider.oninput = function() {
    text = text.replaceAll(/-{2,}/g, '-');
    text = text.replaceAll('|-|', '|');
    text = text.replaceAll('-|', '|');
    text = text.replaceAll(/\|{2,}/g, '|');
    text = text.replaceAll(' ', '');

    output.innerHTML = `BPM: ${this.value}`;
    text_box.innerHTML = `${base_text} ${this.value} ${text.substring(0, text.length - 1)}`;
    char_cnt.innerHTML = `Cheer Message: ${text_box.innerHTML.length} Characters`;
  }

  test_play.onclick = async () => {
    try {
      if (reset != null) clearTimeout(reset);
      if (Tone.Transport.state !== 'started' && song == null) {

        let notation = [];
        if (error == '' && text.substring(0, text.length-1)) {
          let lines = text.substring(0, text.length - 1).split('|');
          let end = 0;

          lines.forEach((line) => {
            let beats = line.split('-');
            let bps = 60 / slider.value;
            let time = 0;
            let length = 1;
            let repeat = false;
            let repeat_list = [];

            for (let index = 0; index < beats.length; index++) {
              let beat = beats[index];
              console.log(`${beat} at ${index}`);
              console.log(beats.toString());
              if (beat == ':') {
                if (repeat) {
                  repeat_list.forEach((rep, rep_index) => {
                    console.log(`Splicing @ ${index + 1 + rep_index} value ${rep}`);
                    beats.splice(index + 1 + rep_index, 0, rep);
                  });
                }

                console.log(beats);
                repeat = !repeat;
                repeat_list = [];
              } else {
                if (repeat) {
                  repeat_list.push(beat);
                }

                let note = beat.split('.');
                note[0] = note[0].replace('*', '');
                if (isNaN(note[0].slice(-1).valueOf())) {
                  note[0] = note[0] + '4'
                }

                if (note.length > 1) {
                  let dotted = note[1].includes('*');
                  if (note[1].includes('/')) {
                    length = note[1].replace('/', '').replace('*', '').valueOf();
                    length = 1 / length;
                  } else {
                    length = note[1].replace('/', '').replace('*', '').valueOf();
                  }
                  if (dotted) length *= 1.5;
                }

                if (!note[0].includes('r')) {
                  notation.push({
                    "note": note[0],
                    "length": length * bps * 0.6,
                    "time": time
                  });
                }
                console.log(`Added ${note[0]} for ${length * bps} at ${time}`);
                time += length * bps;
              }
            };

            end = Math.max(time, end);
          });
          
          console.log(notation);
          song = new Tone.Part((time, note) => {
            synth.triggerAttackRelease(note.note, note.length, time);
          }, notation).start(0);
          Tone.Transport.start();

          test_play.innerHTML = 'Stop Song';

          reset = setTimeout(function() {
            Tone.Transport.stop();
          }, 1000*(end + 1));
        }
      } else {
        Tone.Transport.stop();
      } 
    } catch (ex) {
      console.log(`Error: ${ex}`);
    }
  }

  Tone.Transport.on('stop', () => {
    if (reset != null) clearTimeout(reset);
    song.dispose();
    song = null;
    test_play.innerHTML = 'Test Song';
  });

  const hot = new Handsontable(container, {
    width: '100%',
    height: '20em',
    startCols: 500,
    startRows: 20,
    rowHeaders: true,
    colHeaders: false,
    dragToScroll: true,
    licenseKey: 'non-commercial-and-evaluation',
  });

  hot.addHook('afterChange', (changes) => {
    text = '';
    error = '';
    for (let x = 0; x < 500; x++) {
      let row_text = '';
      for (let y = 0; y < 200; y++) {
        let el = hot.getDataAtCell(x, y);
        if (el != null && el.trim() != '') {
          if (!el.match(/^(:|([a-g]b?[1-9]?\*?|r)(\.\/?[1-8]+\*?)?)$/)) {
            error = `Improper note value at ${y},${x}: ${el}`;
          }
          text += `${el}-`;
          row_text += `-`;
        }
      }
      if (x < 499 && row_text != '') text += '|';
    }

    text = text.replaceAll(/-{2,}/g, '-');
    text = text.replaceAll('|-|', '|');
    text = text.replaceAll('-|', '|');
    text = text.replaceAll(/\|{2,}/g, '|');
    text = text.replaceAll(' ', '');
    
    text_box.innerHTML = `${base_text} ${slider.value} ${text.substring(0, text.length - 1)}`;
    char_cnt.innerHTML = `Cheer Message: ${text_box.innerHTML.length} Characters`;
    error_box.innerHTML = `Errors: ${error}`;
  });
});