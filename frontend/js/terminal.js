/**
 * Offline GPT — Interactive Terminal Command Prompt CLI Widget
 */

document.addEventListener('DOMContentLoaded', () => {
    const terminalWindow = document.getElementById('terminal-window');
    const cliInput = document.getElementById('cli-input');
    const cliExecBtn = document.getElementById('cli-exec-btn');
    const quickCmdBtns = document.querySelectorAll('.cli-cmd-btn');

    const commandHistory = [];
    let historyIndex = -1;

    function appendTerminalLine(text, className = '') {
        const line = document.createElement('div');
        line.className = `term-line ${className}`;
        line.innerText = text;
        terminalWindow.appendChild(line);
        terminalWindow.scrollTop = terminalWindow.scrollHeight;
    }

    async function executeCommand(cmdStr) {
        const cmd = cmdStr.trim();
        if (!cmd) return;

        appendTerminalLine(`offline-gpt@agent:~$ ${cmd}`, 'term-prompt-cmd');
        commandHistory.push(cmd);
        historyIndex = commandHistory.length;
        cliInput.value = '';

        try {
            const data = await ApiClient.executeCli(cmd);

            if (data.type === 'clear') {
                terminalWindow.innerHTML = `
                    <div class="term-line banner-line">======================================================================</div>
                    <div class="term-line banner-line">  OFFLINE GPT INTERACTIVE TERMINAL CLI</div>
                    <div class="term-line banner-line">  Type <span class="term-highlight">/help</span> to view available custom commands.</div>
                    <div class="term-line banner-line">======================================================================</div>
                    <br>
                `;
                return;
            }

            appendTerminalLine(data.output, 'term-output');
        } catch (err) {
            appendTerminalLine(`❌ Command Error: ${err.message}`, 'term-error');
        }
    }

    cliExecBtn.addEventListener('click', () => {
        executeCommand(cliInput.value);
    });

    cliInput.addEventListener('keydown', (e) => {
        if (e.key === 'Enter') {
            e.preventDefault();
            executeCommand(cliInput.value);
        } else if (e.key === 'ArrowUp') {
            e.preventDefault();
            if (historyIndex > 0) {
                historyIndex--;
                cliInput.value = commandHistory[historyIndex];
            }
        } else if (e.key === 'ArrowDown') {
            e.preventDefault();
            if (historyIndex < commandHistory.length - 1) {
                historyIndex++;
                cliInput.value = commandHistory[historyIndex];
            } else {
                historyIndex = commandHistory.length;
                cliInput.value = '';
            }
        }
    });

    quickCmdBtns.forEach(btn => {
        btn.addEventListener('click', () => {
            const cmd = btn.getAttribute('data-cmd');
            cliInput.value = cmd;
            executeCommand(cmd);
        });
    });
});
