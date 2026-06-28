document.addEventListener("DOMContentLoaded", function () {

    function init() {

        const input = document.getElementById("parameter-search");

        const dropdown =
            document.querySelector("#parameter-dropdown .Select-control");

        if (!input || !dropdown)
            return;

        //
        // Clicking the search box opens the dropdown
        //
        input.addEventListener("focus", function () {
            dropdown.dispatchEvent(
                new MouseEvent("mousedown", {
                    bubbles: true
                })
            );
        });

        //
        // Down arrow enters dropdown navigation
        //
        input.addEventListener("keydown", function (e) {

            if (e.key === "ArrowDown") {

                dropdown.dispatchEvent(
                    new MouseEvent("mousedown", {
                        bubbles: true
                    })
                );

                setTimeout(function () {

                    const s = document.querySelector(
                        "#parameter-dropdown input"
                    );

                    if (s)
                        s.focus();

                }, 20);

                e.preventDefault();
            }

        });

    }

    setTimeout(init, 500);

});

