document.addEventListener("DOMContentLoaded", function() {
    let clockElement = document.getElementById("clock");

    if (clockElement) {
        let remainingTimeSeconds = 600; // Alterado para 10 minutos (10 * 60)

        function updateCountdown() {
            let storedRemainingTime = localStorage.getItem("remainingTime");
            let remainingTime;

            if (storedRemainingTime) {
                remainingTime = parseInt(storedRemainingTime);
            } else {
                remainingTime = remainingTimeSeconds;
                localStorage.setItem("remainingTime", remainingTime.toString());
            }

            let hours = Math.floor(remainingTime / 3600);
            let minutes = Math.floor((remainingTime % 3600) / 60);
            let seconds = remainingTime % 60;

            let formattedTime = `${formatTimeComponent(hours)}:${formatTimeComponent(minutes)}:${formatTimeComponent(seconds)}`;
            clockElement.textContent = formattedTime;

            remainingTime--;

            if (remainingTime < 0) {
                clockElement.textContent = "Tempo expirado";
                localStorage.removeItem("remainingTime");
                return;
            }

            localStorage.setItem("remainingTime", remainingTime.toString());

            setTimeout(updateCountdown, 1000);
        }

        function formatTimeComponent(time) {
            return time < 10 ? "0" + time : time;
        }

        // Reiniciar o valor da sessão ao atualizar a página
        window.addEventListener("beforeunload", function() {
            localStorage.removeItem("remainingTime");
        });

        updateCountdown();
    }
});
