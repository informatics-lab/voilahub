import {
  JupyterLab, JupyterLabPlugin
} from '@jupyterlab/application';

import '../style/index.css';
import { LaunchButton } from './btn';


import { IDocumentManager } from '@jupyterlab/docmanager'

/**
 * Initialization data for the henry extension.
 */
const extension: JupyterLabPlugin<void> = {
  id: 'henry',
  autoStart: true,
  requires: [IDocumentManager],

  activate: (app: JupyterLab, documentManger: IDocumentManager) => {
    console.log('JupyterLab extension VoilaHub  0.0.11 is activated!');
    app.docRegistry.addWidgetExtension('Notebook', new LaunchButton(documentManger));
  }
};

export default extension;