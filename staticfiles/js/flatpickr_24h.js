document.addEventListener('DOMContentLoaded', function() {
    // Ensure Italian locale is loaded

    function getNextQuarterHour() {
        const now = new Date();
        let minutes = now.getMinutes();
        let next = Math.ceil(minutes / 15) * 15;
        if (next === 60) {
            now.setHours(now.getHours() + 1);
            next = 0;
        }
        now.setMinutes(next);
        now.setSeconds(0);
        return now;
    }

    // Initialize start picker
    const startPicker = flatpickr('.flatpickr-start', {
        enableTime: true,
        dateFormat: "Y-m-d H:i",
        time_24hr: true,
        minuteIncrement: 15,
        minDate: "today",
        defaultHour: getNextQuarterHour().getHours(),
        defaultMinute: getNextQuarterHour().getMinutes(),
        onReady: function(selectedDates, dateStr, instance) {
            const today = flatpickr.formatDate(new Date(), "Y-m-d");
            if (!instance.selectedDates.length || flatpickr.formatDate(instance.selectedDates[0], "Y-m-d") === today) {
                const minTime = getNextQuarterHour();
                instance.set('minTime', minTime.getHours().toString().padStart(2, '0') + ":" + minTime.getMinutes().toString().padStart(2, '0'));
            } else {
                instance.set('minTime', "00:00");
            }
        },
        onChange: function(selectedDates, dateStr, instance) {
            const today = flatpickr.formatDate(new Date(), "Y-m-d");
            if (selectedDates.length && flatpickr.formatDate(selectedDates[0], "Y-m-d") === today) {
                const minTime = getNextQuarterHour();
                instance.set('minTime', minTime.getHours().toString().padStart(2, '0') + ":" + minTime.getMinutes().toString().padStart(2, '0'));
            } else {
                instance.set('minTime', "00:00");
            }
        },
        monthSelectorType: "static"
    });

    // Initialize end picker
    const endPicker = flatpickr('.flatpickr-end', {
        enableTime: true,
        dateFormat: "Y-m-d H:i",
        time_24hr: true,
        minuteIncrement: 15,
        minDate: "today",
    });

    function updateEndTimeConstraints() {
        if (!startPicker.selectedDates.length) return;

        const startDate = new Date(startPicker.selectedDates[0]);
        const minEndDate = new Date(startDate.getTime() + 60 * 60 * 1000); // +1 hour

        // Set minDate for endPicker
        endPicker.set('minDate', flatpickr.formatDate(minEndDate, "Y-m-d"));

        // If end date is the same as minEndDate, set minTime to minEndDate's time, else "00:00"
        endPicker.set('minTime',
            flatpickr.formatDate(minEndDate, "Y-m-d") === flatpickr.formatDate(endPicker.selectedDates[0] || minEndDate, "Y-m-d")
                ? flatpickr.formatDate(minEndDate, "H:i")
                : "00:00"
        );

        // If selected end time is before minEndDate, clear it
        if (endPicker.selectedDates.length && endPicker.selectedDates[0] < minEndDate) {
            endPicker.clear();
        }
    }

    // Attach updateEndTimeConstraints to startPicker changes
    startPicker.config.onChange.push(updateEndTimeConstraints);

    // Initialize constraints if start time is already set
    if (startPicker.input.value) {
        updateEndTimeConstraints();
    }
});