$(document).ready(() => {
  const slider = document.getElementById('bpm');
  const output = document.getElementById('bpm_value');

  const text_box = document.getElementById('text');
  const char_cnt = document.getElementById('char_count');
  const base_text = '#lute';
  var text = '';

  const container = document.getElementById('datatable');

  output.innerHTML = `BPM: ${slider.value}`;
  text_box.innerHTML = `${base_text} ${slider.value} ${text}`;
  char_cnt.innerHTML = `Cheer Message: ${text_box.innerHTML.length} Characters`;

  slider.oninput = function() {
    text = text.replaceAll(/-{2,}/g, '-');
    text = text.replaceAll('|-|', '|');
    text = text.replaceAll(/\|{2,}/g, '|');
    text = text.replaceAll(' ', '');

    output.innerHTML = `BPM: ${this.value}`;
    text_box.innerHTML = `${base_text} ${this.value} ${text.substring(0, text.length - 1)}`;
    char_cnt.innerHTML = `Cheer Message: ${text_box.innerHTML.length} Characters`;
  }

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
    for (let x = 0; x < 500; x++) {
      let row_text = '';
      for (let y = 0; y < 200; y++) {
        let el = hot.getDataAtCell(x, y);
        if (el != null && el.trim() != '') {
          text += `${el}-`;
          row_text += `-`;
        }
      }
      if (x < 499 && row_text != '') text += '|';
    }

    text = text.replaceAll(/-{2,}/g, '-');
    text = text.replaceAll('|-|', '|');
    text = text.replaceAll(/\|{2,}/g, '|');
    text = text.replaceAll(' ', '');
    
    text_box.innerHTML = `${base_text} ${slider.value} ${text.substring(0, text.length - 1)}`;
    char_cnt.innerHTML = `Cheer Message: ${text_box.innerHTML.length} Characters`;
  });
});