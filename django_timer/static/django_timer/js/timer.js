function pad(number){
    return ('00' + number).slice(-2)
}

function printDuration(duration){
    var seconds = Math.floor(duration)
    var minutes = Math.floor(seconds/60)
    var hours = Math.floor(minutes/60)
    seconds = seconds % 60
    minutes = minutes % 60
    if (hours) {
        return hours + ':' + pad(minutes) + ':' + pad(seconds)
    }
    return pad(minutes) + ':' + pad(seconds)
}

var timer = document.getElementById('django-timer')

if (timer) {
    var duration = timer.getAttribute('value')
    if (duration){
        setInterval(function() {
            duration++
            timer.innerHTML = printDuration(duration)
        }, 1000)
    }
}
