import nontexed.web, ipywidgets

def NONTEXED(s):
    data = nontexed.web.inmem_fmt('[[hr]]\n'+s.strip())
    if set(data) != {'/data/index.html', '/data/hr.html'}:
        raise ValueError("Multiplexing not supported!")
    data = data['/data/hr.html']
    data += '''<img src='data:text/html,' style='display: none' onerror='
(function(cell){
    var div_output = cell.parentNode;
    while((" "+cell.className+" ").indexOf(" cell ") < 0 && (" "+cell.className+" ").indexOf(" jp-Notebook-cell ") < 0)
        cell = cell.parentNode;
    var div_input = cell.querySelector("div.input");
    if(!div_input) //rendered
    {
        div_input = cell.querySelector("div.jp-InputArea");
        div_input.style.display = "none";
        return; //no interaction for you
    }
    var textarea = div_input.querySelector("textarea");
    var old_display = div_input.style.display;
    div_input.style.display = "none";
    var hdlr = function()
    {
        div_input.style.display = old_display;
        while(div_output.firstChild)
            div_output.removeChild(div_output.firstChild);
        cell.removeEventListener("dblclick", hdlr);
        textarea.focus();
    };
    cell.addEventListener("dblclick", hdlr);
})(this)'/>'''
    return ipywidgets.HTML(data)
