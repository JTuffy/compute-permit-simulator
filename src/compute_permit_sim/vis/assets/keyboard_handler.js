
(function () {
    function handleKeyDown(event) {
        // Ignore if focus is in an input or textarea
        if (event.target.tagName === 'INPUT' || event.target.tagName === 'TEXTAREA') {
            return;
        }

        const key = event.key;

        // P or Space -> Play/Pause
        if (key === 'p' || key === 'P' || key === ' ') {
            event.preventDefault(); // Prevent scrolling for space
            // Trigger custom event or call exposed python method?
            // Since we can't easily call python from here without a custom widget,
            // We'll rely on a hidden button click or similar if possible.
            // BUT Solara usually needs specific communication.
            // Actually, we can dispatch a custom event that a Solara component might listen to?
            // No, getting data back to Python is the hard part in pure script.

            // ALTERNATIVE: Use solara.on_key_down on a global div that we force focus to?
            // OR: We rely on the python-side 'KeyboardListener' component which uses
            // solara.v.Use(keydown=...) or similar if available.
        }
    }
    // window.addEventListener('keydown', handleKeyDown);
})();
