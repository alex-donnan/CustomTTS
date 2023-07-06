$(document).ready(() => {
  //Synthesizer
  const synth = new Tone.PolySynth(Tone.Synth).toDestination();
  synth.set({
    envelope: {
      attack: 0.,
      decay: 0.1,
      sustain: 0.25
    }
  });
  synth.volume.value = -12;

  //Rest of it
  const import_text = document.getElementById('import_text');
  const import_butt = document.getElementById('import_button');

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
  var save_data = {
    tempo: 120,
    data: []
  }

  const container = document.getElementById('datatable');

  output.innerHTML = `BPM: ${slider.value}`;
  text_box.innerHTML = `${base_text} ${slider.value} ${text}`;
  char_cnt.innerHTML = `Cheer Message: ${text_box.innerHTML.length} Characters`;

  slider.oninput = () => {
    text = text.replaceAll(/-{2,}/g, '-');
    text = text.replaceAll('|-|', '|');
    text = text.replaceAll('-|', '|');
    text = text.replaceAll(/\|{2,}/g, '|');
    text = text.replaceAll(' ', '');

    output.innerHTML = `BPM: ${slider.value}`;
    text_box.innerHTML = `${base_text} ${slider.value} ${text.substring(0, text.length - 1)}`;
    char_cnt.innerHTML = `Cheer Message: ${text_box.innerHTML.length} Characters`;

    save_data.tempo = slider.value;
    localStorage.setItem("luting", JSON.stringify(save_data));
  }

  import_butt.onclick = () => {
    if (import_text.value != '') {
      let import_val = import_text.value.replace('#lute', '').trim().split(' ');
      if (import_val.length == 1) {
        import_val[1] = import_val[0];
        import_val[0] = 120;
      }
      slider.value = import_val[0].valueOf();
      output.innerHTML = `BPM: ${slider.value}`;
      let import_arr = import_val[1].split('|');
      let data = [];
      let len_dict = {};
      let low_tempo = '1';
      let low_tempo_val = 1;

      import_arr.forEach((line) => {
        let line_arr = line.split('-');

        line_arr.forEach((el, ind) => {
          let note = el.split('.');
          let length = 1

          if (note.length > 1) {
            let dotted = note[1].includes('*');
            if (note[1].includes('/')) {
              length = note[1].replace('/', '').replace('*', '').valueOf();
              length = 1 / length;
            } else {
              length = note[1].replace('/', '').replace('*', '').valueOf();
            }
            if (dotted) length *= 1.5;

            if (length < low_tempo_val) {
              low_tempo_val = length;
              low_tempo = note[1];
            }

            if (len_dict[note[1]] == undefined) {
              len_dict[note[1]] = length;
            }
          }
        });
      });

      import_arr.forEach((line) => {
        let line_arr = line.split('-');
        let last_tempo = '1';
        let line_new = [];
        let repeat = false;

        line_arr.forEach((el, ind) => {
          let note = el.split('.');
          let new_note = el;

          if (note.length > 1) {
            if (note[1] != last_tempo) {
              last_tempo = note[1];
            } else {
              if (repeat) {
                last_tempo = note[1];
              } else {
                new_note = note[0];
              }
            }
            repeat = false;
          } else {
            if (note[0] == ':') {
              repeat = true;
            } else if (note[0].match(/^([a-g]b?[1-8]?\*?|r)?$/) && repeat) {
              new_note = `${el}.${last_tempo}`;
              repeat = false;
            }
          }

          line_new.push(new_note);
          if (note[0] != ':') {
            for (let i = 1; i < Math.ceil(len_dict[last_tempo] / low_tempo_val); i++) {
              line_new.push('');
            }
          }
        });
        data.push(line_new);
      });
      hot.clear();
      hot.populateFromArray(0, 0, data);
      import_text.value = '';
    }
  }

  test_play.onclick = async () => {
    console.log(text);
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
    colHeaders: true,
    dragToScroll: true,
    licenseKey: 'non-commercial-and-evaluation',
  });

  hot.addHook('afterChange', (changes) => {
    console.log('updating text');
    text = '';
    let error = '';
    let warn = '';
    let max_w = 0;
    let max_h = 0;
    for (let x = 0; x < 20; x++) {
      let row_text = '';
      let repeat = false;
      for (let y = 0; y < 500; y++) {
        let el = hot.getDataAtCell(x, y);
        if (el != null && el != undefined && el.trim() != '') {
          if (!el.match(/^(:|([a-g]b?[1-8]?\*?|r)(\.\/?[1-9]\d*\*?)?)$/)) {
            error = `Improper note value at ${hot.getColHeader(y)},${x+1}: ${el}`;
            repeat = false;
          } else if (el == ':') {
            repeat = true;
          } else {
            if (repeat && el.split('.').length != 2) {
              warn = `Beat value missing at ${hot.getColHeader(y)},${x+1}: ${el}`;
            }
            repeat = false;
          }
          text += `${el}-`;
          row_text += `-`;
          max_w = Math.max(max_w, y);
          max_h = Math.max(max_h, x);
        }
      }
      if (x < 499 && row_text != '') text += '|';
    }

    text = text.replaceAll(/-{2,}/g, '-');
    text = text.replaceAll('|-|', '|');
    text = text.replaceAll('-|', '|');
    text = text.replaceAll(/\|{2,}/g, '|');
    text = text.replaceAll(' ', '');
    
    output.innerHTML = `BPM: ${slider.value}`;
    text_box.innerHTML = `${base_text} ${slider.value} ${text.substring(0, text.length - 1)}`;
    char_cnt.innerHTML = `Cheer Message: ${text_box.innerHTML.length} Characters`;
    error_box.innerHTML = `Errors: ${error}<br>Warnings: ${warn}`;

    save_data = {
      tempo: slider.value,
      data: hot.getData(max_h, max_w)
    };
    console.log(save_data);
    localStorage.setItem("luting", JSON.stringify(save_data));
  });

  if (localStorage.getItem('luting')) {
    save_data = JSON.parse(localStorage.getItem('luting'));
    slider.value = save_data.tempo;
    hot.populateFromArray(0, 0, Array.from(save_data.data));
  }
});