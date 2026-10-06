# Sandcastle-Probelauf

Der Sandcastle-Ablauf über Integrations-Branches und Pull Requests (#335) ist bisher nur gegen Fakes getestet. Der Probelauf schickt eine minimale Probe-Spec mit zwei Tickets einmal echt durch diesen Ablauf, vom Integrations-Branch `spec/<n>` bis zum PR nach `main` (vgl. #344). Er zeigt, ob die echte Verdrahtung mit `git` und `gh` trägt; Anwendungscode ändert er nicht.
