from flask import Flask, render_template, request, redirect, url_for
import sqlite3
import traceback


conn = sqlite3.connect('notas.db')
c = conn.cursor()
c.execute('''CREATE TABLE IF NOT EXISTS notas
                (aluno text, nota float)''')
conn.commit()

app = Flask(__name__, template_folder='templates')

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/cadastro', methods=['GET', 'POST'])
def cadastro():
    if request.method == 'POST':
        aluno = request.form['aluno']
        nota = request.form['nota']
        c.execute('INSERT INTO notas VALUES (?, ?)', (aluno, nota))
        conn.commit()
        return redirect(url_for('cadastro_sucesso'))
    return render_template('cadastro.html')

@app.route('/cadastro_sucesso')
def cadastro_sucesso():
    return render_template('cadastro_sucesso.html')

@app.route('/notas')
def notas():
    filtro_aluno = request.args.get('filtro_aluno', '')
    filtro_nota = request.args.get('filtro_nota', '')
    if filtro_aluno or filtro_nota:
        notas = c.execute('SELECT * FROM notas WHERE aluno LIKE ? AND nota LIKE ?', 
                            ('%{}%'.format(filtro_aluno), '%{}%'.format(filtro_nota)))
    else:
        notas = c.execute('SELECT * FROM notas')
    notas = notas.fetchall()
    return render_template('notas.html', notas=notas)

@app.route('/limpar_notas')
def limpar_notas():
    c.execute('DELETE FROM notas')
    conn.commit()
    return render_template('limpar_notas.html')

@app.errorhandler(Exception)
def handle_exception(e):
    traceback.print_exc()
    return "An error occurred: {}".format(str(e)), 500

if __name__ == '__main__':
    app.run(debug=True)