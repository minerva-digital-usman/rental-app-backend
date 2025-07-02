window.addEventListener('DOMContentLoaded', function() {
    flatpickr('.flatpickr', {
        enableTime: true,
        dateFormat: "Y-m-d H:i",
        time_24hr: true
    });
});