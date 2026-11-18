document.querySelectorAll("[data-toggle-password]").forEach(function (boton) {
  var campo = document.getElementById(boton.dataset.togglePassword);
  boton.addEventListener("click", function () {
    var visible = campo.type === "text";
    campo.type = visible ? "password" : "text";
    boton.textContent = visible ? "Mostrar" : "Ocultar";
    boton.setAttribute("aria-pressed", String(!visible));
  });
});
