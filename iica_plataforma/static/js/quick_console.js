let tasks = []
let current = 0

function renderTask(){

    if(tasks.length === 0){
        document.getElementById("taskFeed").innerHTML = "Sin tareas"
        return
    }

    let t = tasks[current]

    document.getElementById("taskFeed").innerHTML = `
        <div class="task-card">
            <strong>${t.titulo}</strong><br>
            ${t.proyecto || ""}
        </div>
    `
}

document.getElementById("nextTask").onclick = ()=>{
    if(tasks.length === 0) return
    current = (current + 1) % tasks.length
    renderTask()
}

document.getElementById("prevTask").onclick = ()=>{
    if(tasks.length === 0) return
    current = (current - 1 + tasks.length) % tasks.length
    renderTask()
}

async function loadPriorityTasks(){

    const r = await fetch("/api/tareas/prioridad/")
    tasks = await r.json()

    renderTask()
}

document.getElementById("quickTaskForm").onsubmit = async function(e){

    e.preventDefault()

    let titulo = document.getElementById("quickTaskInput").value

    await fetch("/api/tareas/crear/",{
        method:"POST",
        headers:{
            "Content-Type":"application/json",
            "X-CSRFToken":getCookie("csrftoken")
        },
        body:JSON.stringify({
            titulo:titulo
        })
    })

    document.getElementById("quickTaskInput").value=""

    loadPriorityTasks()
}

loadPriorityTasks()