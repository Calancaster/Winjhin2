function openTopChamps(evt, tabName) {
    
    var i, mostplayedtable, tablinks;

    mostplayedtable = document.getElementsByClassName("most-played-table");
    for (i = 0; i < mostplayedtable.length; i++) {
        mostplayedtable[i].style.display = "none";
    }

    tablinks = document.getElementsByClassName("tablinks");
    for (i = 0; i < tablinks.length; i++) {
        tablinks[i].className = tablinks[i].className.replace(" active", "");
    }

    document.getElementById(tabName).style.display = "table";
    evt.currentTarget.className += " active";
}